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
            using var game = AssemblyDefinition.ReadAssembly(Path.Combine(Path.GetDirectoryName(file)!, "OTAPI.dll"));
            foreach (var field in game.MainModule.Types.Single(t => t.FullName == "Terraria.Main").Fields
                    .Where(f => f.Name.Contains("Release") || f.Name.Contains("Version")))
                Console.WriteLine("GAME_FIELD " + field.Name + "=" + field.Constant);
            foreach (var logMethod in game.MainModule.Types.Single(t => t.FullName == "Terraria.NetMessage").Methods
                    .Where(m => m.Name.Contains("LogMessageError") && m.HasBody))
                foreach (var instruction in logMethod.Body.Instructions) Console.WriteLine("GAME_LOG_IL " + instruction);
            var method = assembly.MainModule.Types.Single(t => t.FullName == "TerrariaApi.Server.Program")
                .Methods.Single(m => m.Name == "Main");
            var init = method.Body.Instructions.Single(i => i.Operand is MethodReference r && r.Name == "InitialiseInternals");
            var attach = method.Body.Instructions.Single(i => i.Operand is MethodReference r && r.Name == "AttachOTAPIHooks");
            if (method.Body.Instructions.IndexOf(init) >= method.Body.Instructions.IndexOf(attach))
                throw new Exception("Unexpected initialization sequence");
            var reference = (MethodReference)init.Operand;
            init.OpCode = OpCodes.Nop; init.Operand = null;
            method.Body.GetILProcessor().InsertAfter(attach, Instruction.Create(OpCodes.Call, reference));
        } else throw new Exception("Unknown patch mode");
        string temporary = file + ".patched";
        assembly.Write(temporary);
        File.Move(temporary, file, true);
        Console.WriteLine("Applied native Mono adaptation: " + mode);
    }
}
