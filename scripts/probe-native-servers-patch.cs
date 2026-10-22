// Diagnostic adaptation: Mono lacks CoreCLR's private stack-trace logging APIs.
using Mono.Cecil;
using Mono.Cecil.Cil;
using System;
using System.Linq;
using System.IO;

class Patch {
    static void Main(string[] args) {
        using var resolver = new DefaultAssemblyResolver();
        resolver.AddSearchDirectory(Path.GetDirectoryName(typeof(object).Assembly.Location));
        foreach (var path in Directory.EnumerateFiles(Path.GetDirectoryName(args[0])!, "*.dll", SearchOption.AllDirectories)
                .Select(Path.GetDirectoryName).Distinct()) resolver.AddSearchDirectory(path!);
        using var assembly = AssemblyDefinition.ReadAssembly(args[0], new ReaderParameters {
            InMemory = true, AssemblyResolver = resolver, ReadingMode = ReadingMode.Immediate
        });
        var type = assembly.MainModule.Types.Single(t => t.FullName == "Terraria.ModLoader.Engine.LoggingHooks");
        var method = type.Methods.Single(m => m.Name == "PrettifyStackTraceSources" && !m.HasParameters);
        if (!method.HasBody || method.ReturnType.FullName != "System.Void") throw new Exception("Unexpected logging method");
        method.Body = new MethodBody(method);
        method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
        string temporary = args[0] + ".patched";
        assembly.Write(temporary);
        File.Move(temporary, args[0], true);
        Console.WriteLine("Disabled only the cosmetic CoreCLR-specific stack-trace logging hook for the native Mono probe.");
    }
}
