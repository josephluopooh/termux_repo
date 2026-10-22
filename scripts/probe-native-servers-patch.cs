// Diagnostic adaptation: Mono lacks CoreCLR's private stack-trace logging APIs.
using Mono.Cecil;
using Mono.Cecil.Cil;
using System;
using System.Linq;

class Patch {
    static void Main(string[] args) {
        using var assembly = AssemblyDefinition.ReadAssembly(args[0], new ReaderParameters { InMemory = true });
        var type = assembly.MainModule.Types.Single(t => t.FullName == "Terraria.ModLoader.Engine.LoggingHooks");
        var method = type.Methods.Single(m => m.Name == "PrettifyStackTraceSources" && !m.HasParameters);
        if (!method.HasBody || method.ReturnType.FullName != "System.Void") throw new Exception("Unexpected logging method");
        method.Body = new MethodBody(method);
        method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
        assembly.Write(args[0]);
        Console.WriteLine("Disabled only the cosmetic CoreCLR-specific stack-trace logging hook for the native Mono probe.");
    }
}
