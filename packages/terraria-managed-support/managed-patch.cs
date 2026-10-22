// Local setup adaptation; game assemblies are downloaded from their publishers.
using Mono.Cecil;
using Mono.Cecil.Cil;
using System;
using System.Linq;
using System.IO;

class Patch {
    static void Main(string[] args) {
        string mode = args[0], file = Path.GetFullPath(args[1]);
        using var resolver = new DefaultAssemblyResolver();
        resolver.AddSearchDirectory(Path.GetDirectoryName(typeof(object).Assembly.Location));
        foreach (var path in Directory.EnumerateFiles(Path.GetDirectoryName(file)!, "*.dll", SearchOption.AllDirectories)
                .Select(Path.GetDirectoryName).Distinct()) resolver.AddSearchDirectory(path!);
        using var assembly = AssemblyDefinition.ReadAssembly(file, new ReaderParameters {
            InMemory = true, AssemblyResolver = resolver, ReadingMode = ReadingMode.Immediate
        });
        if (mode == "tmodloader") {
            var type = assembly.MainModule.Types.Single(t => t.FullName == "Terraria.ModLoader.Engine.LoggingHooks");
            var method = type.Methods.Single(m => m.Name == "PrettifyStackTraceSources" && !m.HasParameters);
            if (!method.HasBody || method.ReturnType.FullName != "System.Void") throw new Exception("Unexpected logging method");
            method.Body = new MethodBody(method);
            method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
        } else if (mode == "tshock") {
            // The local extractor flattens upstream's bin directory. The
            // launcher's fallback resolver still probes bin; point that exact
            // resolver at the adapted application directory instead.
            string launcherFile = Path.Combine(Path.GetDirectoryName(file)!, "TShock.Server.dll");
            using (var launcher = AssemblyDefinition.ReadAssembly(launcherFile, new ReaderParameters { InMemory = true })) {
                var binding = launcher.MainModule.GetTypes().SelectMany(t => t.Methods)
                    .Single(m => m.Name.Contains("Default_Resolving") && m.HasBody);
                var directory = binding.Body.Instructions.Single(i => i.OpCode == OpCodes.Ldstr && (string)i.Operand == "bin");
                directory.Operand = ".";
                launcher.Write(launcherFile + ".patched");
            }
            File.Move(launcherFile + ".patched", launcherFile, true);
            Console.WriteLine("Adapted TShock fallback resolver to the extracted application directory");
            // The checksum-pinned official NuGet runtime asset is IL-only and
            // unsigned. Reject the non-executable reference-assembly fallback;
            // mark it AnyCPU so 64-bit ARM Mono can load the referenced types.
            // This does not enable Steam or supply a native Steam library.
            string steamFile = Path.Combine(Path.GetDirectoryName(file)!, "Steamworks.NET.dll");
            using (var steam = AssemblyDefinition.ReadAssembly(steamFile, new ReaderParameters { InMemory = true })) {
                if (steam.Name.Name != "Steamworks.NET" || steam.Name.Version != new Version(2024, 8, 0, 0) ||
                        steam.CustomAttributes.Any(a => a.AttributeType.FullName == "System.Runtime.CompilerServices.ReferenceAssemblyAttribute") ||
                        steam.Name.HasPublicKey || steam.MainModule.Architecture != TargetArchitecture.AMD64 ||
                        steam.MainModule.Attributes != ModuleAttributes.ILOnly)
                    throw new Exception("Unexpected Steamworks.NET managed architecture");
                steam.MainModule.Architecture = TargetArchitecture.I386;
                steam.Write(steamFile + ".patched");
            }
            File.Move(steamFile + ".patched", steamFile, true);
            Console.WriteLine("Adapted IL-only Steamworks.NET AMD64 metadata to AnyCPU for ARM64 Mono");
            using var game = AssemblyDefinition.ReadAssembly(Path.Combine(Path.GetDirectoryName(file)!, "OTAPI.dll"));
            foreach (var field in game.MainModule.Types.Single(t => t.FullName == "Terraria.Main").Fields
                    .Where(f => f.Name.Contains("Release") || f.Name.Contains("Version")))
                Console.WriteLine("GAME_FIELD " + field.Name + "=" + field.Constant);
            // Log exception type/message before the original logger calls ToString.
            // Mono's formatter can abort on DynamicMethod metadata, hiding the
            // underlying protocol failure. Keep the original logger and behavior.
            var logMethod = game.MainModule.Types.Single(t => t.FullName == "Terraria.NetMessage")
                .Methods.Single(m => m.Name == "mfwh_LogMessageError" && m.HasBody);
            if (logMethod.Parameters.Count != 3 || logMethod.Parameters[2].ParameterType.FullName != "System.Exception")
                throw new Exception("Unexpected protocol logger signature");
            var logIL = logMethod.Body.GetILProcessor();
            var first = logMethod.Body.Instructions[0];
            var write = game.MainModule.ImportReference(typeof(Console).GetMethod("WriteLine", new[] { typeof(string) })!);
            foreach (var instruction in new[] {
                Instruction.Create(OpCodes.Ldstr, "ORIGINAL_PROTOCOL_EXCEPTION"),
                Instruction.Create(OpCodes.Call, write),
                Instruction.Create(OpCodes.Ldarg_2),
                Instruction.Create(OpCodes.Brfalse, first),
                Instruction.Create(OpCodes.Ldarg_2),
                Instruction.Create(OpCodes.Callvirt, game.MainModule.ImportReference(typeof(object).GetMethod("GetType")!)),
                Instruction.Create(OpCodes.Callvirt, game.MainModule.ImportReference(typeof(Type).GetProperty("FullName")!.GetMethod!)),
                Instruction.Create(OpCodes.Call, write),
                Instruction.Create(OpCodes.Ldarg_2),
                Instruction.Create(OpCodes.Callvirt, game.MainModule.ImportReference(typeof(Exception).GetProperty("Message")!.GetMethod!)),
                Instruction.Create(OpCodes.Call, write)
            }) logIL.InsertBefore(first, instruction);
            string gameFile = Path.Combine(Path.GetDirectoryName(file)!, "OTAPI.dll");
            game.Write(gameFile + ".patched");
            game.Dispose();
            File.Move(gameFile + ".patched", gameFile, true);
            var method = assembly.MainModule.Types.Single(t => t.FullName == "TerrariaApi.Server.Program")
                .Methods.Single(m => m.Name == "Main");
            var init = method.Body.Instructions.Single(i => i.Operand is MethodReference r && r.Name == "InitialiseInternals");
            var attach = method.Body.Instructions.Single(i => i.Operand is MethodReference r && r.Name == "AttachOTAPIHooks");
            if (method.Body.Instructions.IndexOf(init) >= method.Body.Instructions.IndexOf(attach))
                throw new Exception("Unexpected initialization sequence");
            var reference = (MethodReference)init.Operand;
            init.OpCode = OpCodes.Nop; init.Operand = null;
            method.Body.GetILProcessor().InsertAfter(attach, Instruction.Create(OpCodes.Call, reference));
            // Mono can initialize ServerApi while JIT-compiling this method,
            // before its first instruction executes. ServerApi's cctor writes
            // Main.SkipAssemblyLoad, which initializes Main.WorldPath from the
            // still-null Terraria.Program.SavePath. Keep path preparation in a
            // separate, non-inlined entry point before any ServerApi reference.
            var program = method.DeclaringType;
            if (program.Methods.Any(m => m.Name == "RunPrepared"))
                throw new Exception("Native bootstrap is already present");
            var prepare = program.Methods.Single(m => m.Name == "PrepareSavePath");
            var prepareCall = method.Body.Instructions.Single(i => i.Operand is MethodReference r && r.Name == "PrepareSavePath");
            if (prepareCall.Previous.OpCode != OpCodes.Ldarg_0 || method.Parameters.Count != 1 ||
                    method.ReturnType.FullName != "System.Void")
                throw new Exception("Unexpected path preparation sequence");
            prepareCall.Previous.OpCode = OpCodes.Nop;
            prepareCall.OpCode = OpCodes.Nop; prepareCall.Operand = null;
            var entry = new MethodDefinition("Main", method.Attributes, method.ReturnType);
            entry.Parameters.Add(new ParameterDefinition("args", ParameterAttributes.None, method.Parameters[0].ParameterType));
            entry.ImplAttributes |= MethodImplAttributes.NoInlining;
            prepare.ImplAttributes |= MethodImplAttributes.NoInlining;
            method.ImplAttributes |= MethodImplAttributes.NoInlining;
            method.Name = "RunPrepared";
            method.IsPublic = false; method.IsPrivate = true;
            program.Methods.Add(entry);
            var bootstrap = entry.Body.GetILProcessor();
            // Load the verified local managed dependency before Mono JITs
            // the server entry path. This also exposes a direct binding error
            // before protocol logging can obscure it in DynamicMethod frames.
            bootstrap.Append(Instruction.Create(OpCodes.Call, assembly.MainModule.ImportReference(
                typeof(AppContext).GetProperty("BaseDirectory")!.GetMethod!)));
            bootstrap.Append(Instruction.Create(OpCodes.Ldstr, "Steamworks.NET.dll"));
            bootstrap.Append(Instruction.Create(OpCodes.Call, assembly.MainModule.ImportReference(
                typeof(Path).GetMethod("Combine", new[] { typeof(string), typeof(string) })!)));
            bootstrap.Append(Instruction.Create(OpCodes.Call, assembly.MainModule.ImportReference(
                typeof(System.Reflection.Assembly).GetMethod("LoadFrom", new[] { typeof(string) })!)));
            bootstrap.Append(Instruction.Create(OpCodes.Pop));
            bootstrap.Append(Instruction.Create(OpCodes.Ldarg_0));
            bootstrap.Append(Instruction.Create(OpCodes.Call, prepare));
            bootstrap.Append(Instruction.Create(OpCodes.Ldarg_0));
            bootstrap.Append(Instruction.Create(OpCodes.Call, method));
            bootstrap.Append(Instruction.Create(OpCodes.Ret));
            if (assembly.MainModule.EntryPoint == method) assembly.MainModule.EntryPoint = entry;
            var error = assembly.MainModule.Types.Single(t => t.FullName == "TerrariaApi.Server.Program")
                .Methods.Single(m => m.Name == "UnhandledException");
            error.Body = new MethodBody(error);
            var il = error.Body.GetILProcessor();
            il.Append(Instruction.Create(OpCodes.Ldarg_1));
            il.Append(Instruction.Create(OpCodes.Callvirt, assembly.MainModule.ImportReference(
                typeof(UnhandledExceptionEventArgs).GetProperty("ExceptionObject")!.GetMethod!)));
            il.Append(Instruction.Create(OpCodes.Call, assembly.MainModule.ImportReference(
                typeof(Console).GetMethod("WriteLine", new[] { typeof(object) })!)));
            il.Append(Instruction.Create(OpCodes.Ret));
        } else throw new Exception("Unknown patch mode");
        string temporary = file + ".patched";
        assembly.Write(temporary);
        File.Move(temporary, file, true);
        Console.WriteLine("Applied native Mono adaptation: " + mode);
    }
}
