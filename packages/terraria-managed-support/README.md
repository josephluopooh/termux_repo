# Native managed-server support

This application-local dependency supplies a Bionic port of MonoMod.Core 1.3.2,
MonoMod.RuntimeDetour 25.3.2, a small ARM64 instruction-cache helper, and a local
assembly setup tool. It does not replace system runtime libraries. The official
Termux .NET runtime remains responsible for managed execution.

The upstream MonoMod Android backend is unimplemented. This source adaptation
uses Bionic errno and page-size functions, Termux's temporary directory, and
instruction-cache maintenance after code patches. The test suite exercises
1,000 hooks, exception propagation and removal. Physical Android devices,
16 KB kernels, and arbitrary third-party mods need further testing.

Sources: MonoMod commit `1fea03f95352a70268a069e68b232c8be0c7f296`, iced commit
`c50f29b7bc305696895c075f3fc7719751426b12`. MIT licenses and dependency notices
are retained. The setup code and instruction-cache helper are Apache-2.0.
The NuGet runtime dependencies are pinned: Mono.Cecil 0.11.6, MonoMod.Core
1.3.2, MonoMod.RuntimeDetour 25.3.2, MonoMod.Utils 25.0.10,
MonoMod.Backports 1.1.2 and MonoMod.ILHelpers 1.1.0. The Core assembly is replaced
with the source-built Bionic adaptation. The package records the dependency
lock file, NuGet archive hashes, and the exact source URLs and hashes of
copyright/permission notices omitted from those NuGet archives.

This missing dependency is private support for the requested
servers; existing official Mono/.NET/SQLite/SDL packages are reused.

Server payloads are downloaded from their upstream publishers only during an
explicit setup command. No Terraria assemblies are redistributed in this package.
