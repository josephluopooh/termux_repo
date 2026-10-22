#!/usr/bin/env bash
set -euo pipefail
mkdir -p native-probe/{sdk,tshock-src,tmodloader} probe-evidence
fetch() {
    curl --fail --location --retry 3 "$1" --output "$2"
    printf '%s  %s\n' "$3" "$2" | sha256sum -c -
}
fetch 'https://codeload.github.com/Pryaxis/TShock/tar.gz/refs/tags/v6.2.1' native-probe/tshock.tar.gz fa62cacdfa4596de3357a79f32d28250ede4f3d7a88beed762f22b00765c680e
fetch 'https://codeload.github.com/NyxStudios/TerrariaAPI-Server/tar.gz/33cbc2a598a7173f63e23d420b70f1be17f27844' native-probe/api.tar.gz 26ac8e7ae5a79c2e23b1232a20437a55ced0781e60b9295c4d13681c637fe2e3
tar -xf native-probe/tshock.tar.gz -C native-probe/tshock-src --strip-components=1
tar -xf native-probe/api.tar.gz -C native-probe/tshock-src/TerrariaServerAPI --strip-components=1
curl --fail --location --retry 3 'https://builds.dotnet.microsoft.com/dotnet/Sdk/9.0.319/dotnet-sdk-9.0.319-linux-arm64.tar.gz' -o native-probe/sdk.tar.gz
printf '%s  %s\n' 940b056511b078c4ab15318f3a7a6114c57c6c636ab32027e90129e3f8b205236a1c6af794eb35a887d7bf3219ff49522da2cb9f9a6d5d26e390909c25536ed2 native-probe/sdk.tar.gz | sha512sum -c -
tar -xf native-probe/sdk.tar.gz -C native-probe/sdk
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_ROOT="$PWD/native-probe/sdk"
export PATH="$DOTNET_ROOT:$PATH"
# A portable, framework-dependent assembly; no Linux apphost or bundled runtime.
# Keep libraries beside the assembly so the standard deps.json resolver can find them.
sed -i 's/<Target Name="MovePublishBin" AfterTargets="Publish">/<Target Name="MovePublishBin" AfterTargets="Publish" Condition="false">/' native-probe/tshock-src/TShockLauncher/TShockLauncher.csproj
python3 - <<'PY'
from pathlib import Path
for p in Path('native-probe/tshock-src').rglob('*.csproj'):
    text = p.read_text(encoding='utf-8-sig')
    old = '<PackageReference Include="Microsoft.Data.Sqlite" Version="9.0.0" />'
    text = text.replace(old, '<PackageReference Include="Microsoft.Data.Sqlite.Core" Version="9.0.0" />\n<PackageReference Include="SQLitePCLRaw.bundle_sqlite3" Version="2.1.10" />')
    p.write_text(text)
launcher = Path('native-probe/tshock-src/TShockLauncher/Program.cs')
text = launcher.read_text(encoding='utf-8-sig')
text = text.replace('Dictionary<string, Assembly> _cache', 'AppDomain.CurrentDomain.UnhandledException += (_, e) => Console.Error.WriteLine(e.ExceptionObject);\n\nDictionary<string, Assembly> _cache')
launcher.write_text(text)
api = Path('native-probe/tshock-src/TerrariaServerAPI/TerrariaServerAPI/Program.cs')
text = api.read_text()
text = text.replace('ServerApi.LogWriter.ServerWriteLine("Server crashed', 'Console.Error.WriteLine("Original initialization exception: " + ex);\n\t\t\t\tServerApi.LogWriter.ServerWriteLine("Server crashed')
# Mono eagerly initializes the game tables while registering custom item sets.
# Attach OTAPI's constructor hooks before those tables can trigger Main's cctor.
old = 'InitialiseInternals();\n\t\t\t\tServerApi.Hooks.AttachOTAPIHooks(args);'
assert old in text
text = text.replace(old, 'ServerApi.Hooks.AttachOTAPIHooks(args);\n\t\t\t\tInitialiseInternals();')
api.write_text(text)
PY
result=0
dotnet publish native-probe/tshock-src/TShockLauncher -c Release -f net9.0 \
    --no-self-contained -p:UseAppHost=false -p:PublishSingleFile=false \
    -o "$PWD/native-probe/tshock" 2>&1 | tee probe-evidence/tshock-build.log || result=1
fetch 'https://github.com/tModLoader/tModLoader/releases/download/v2026.08.3.0/tModLoader.zip' native-probe/tmodloader.zip 61e865f3702b12ce4a26c5a90b9de99a12c65ffc228455eb3390ce54af1eab15
unzip -q native-probe/tmodloader.zip -d native-probe/tmodloader
# Build an isolated source-port experiment. Never ship this as a supported runtime.
mkdir -p native-probe/monomod
fetch 'https://codeload.github.com/MonoMod/MonoMod/tar.gz/1fea03f95352a70268a069e68b232c8be0c7f296' native-probe/monomod.tar.gz 1154cfaa8986aa04e7d18432172402f7fc8a84d8bf3e66f7f7357db359f1bc59
fetch 'https://codeload.github.com/icedland/iced/tar.gz/c50f29b7bc305696895c075f3fc7719751426b12' native-probe/iced.tar.gz c5f2473db51e3ab6c48a2c4dcf099e5b29f16ef83b251c46868cb68025b1d7e7
tar -xf native-probe/monomod.tar.gz -C native-probe/monomod --strip-components=1
mkdir -p native-probe/monomod/external/iced
tar -xf native-probe/iced.tar.gz -C native-probe/monomod/external/iced --strip-components=1
python3 scripts/probe-native-servers-monomod.py native-probe/monomod
if dotnet build native-probe/monomod/src/MonoMod.Core/MonoMod.Core.csproj -c Release -f net8.0 \
    -p:RestoreLockedMode=false -p:MMBannedApis=false -p:EnableNETAnalyzers=false -p:DoNotAddSuffix=true \
    2>&1 | tee probe-evidence/monomod-build.log; then
    cp -r native-probe/tmodloader native-probe/tmodloader-patched
    core=$(find native-probe/monomod/artifacts/bin/MonoMod.Core -path '*net8.0/MonoMod.Core.dll' -print -quit)
    test -n "$core"
    find native-probe/tmodloader-patched/Libraries -name MonoMod.Core.dll -exec cp "$core" '{}' \;
    mkdir -p native-probe/detour-src
    cat > native-probe/detour-src/detour.csproj <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings></PropertyGroup><ItemGroup><PackageReference Include="MonoMod.RuntimeDetour" Version="25.3.2" /></ItemGroup></Project>
XML
    cat > native-probe/detour-src/Program.cs <<'CS'
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using MonoMod.RuntimeDetour;
using MonoMod.Core.Platforms;
class Probe {
    [MethodImpl(MethodImplOptions.NoInlining)]
    public static int Original(int value) => value < 0 ? throw new InvalidOperationException("unwind-check") : value + 1;
    public static void Main() {
        Console.WriteLine($"{RuntimeInformation.FrameworkDescription} {RuntimeInformation.RuntimeIdentifier} pagesize={Environment.SystemPageSize}");
        Console.WriteLine($"MonoMod system={PlatformTriple.Current.System.Target}");
        using (var hook = new Hook(typeof(Probe).GetMethod(nameof(Original))!, (Func<Func<int,int>,int,int>)((orig, value) => orig(value) + 10))) {
            for (int i=0; i<1000; i++) if (Original(i) != i+11) throw new Exception("Hook/cache flush failed");
            try { Original(-1); throw new Exception("Missing expected exception"); }
            catch (InvalidOperationException e) when (e.Message == "unwind-check") { }
        }
        if (Original(7) != 8) throw new Exception("Unhook failed");
        Console.WriteLine("PASS: 1000 ARM64 managed detours, exception propagation, unhook");
    }
}
CS
    dotnet publish native-probe/detour-src -c Release --no-self-contained -p:UseAppHost=false -o "$PWD/native-probe/detour"
    cp "$core" native-probe/detour/MonoMod.Core.dll
    # Keep the tested MonoMod family private to this experimental server tree.
    cp "$core" native-probe/tshock/MonoMod.Core.dll
    for library in MonoMod.Utils MonoMod.RuntimeDetour; do
        cp "native-probe/detour/$library.dll" "native-probe/tshock/$library.dll"
    done
    mkdir -p native-probe/patch-src
    cat > native-probe/patch-src/patch.csproj <<'XML'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net9.0</TargetFramework></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="0.11.6" /></ItemGroup></Project>
XML
    cp scripts/probe-native-servers-patch.cs native-probe/patch-src/Program.cs
    dotnet run --project native-probe/patch-src -c Release -- native-probe/tmodloader-patched/tModLoader.dll
    touch native-probe/tmodloader-patched/.native-patch-complete
else
    result=1
fi
# Only logs are uploaded. Proprietary server payloads stay in this disposable runner.
exit "$result"
