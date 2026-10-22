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
PY
result=0
dotnet publish native-probe/tshock-src/TShockLauncher -c Release -f net9.0 \
    --no-self-contained -p:UseAppHost=false -p:PublishSingleFile=false \
    -o "$PWD/native-probe/tshock" 2>&1 | tee probe-evidence/tshock-build.log || result=1
fetch 'https://github.com/tModLoader/tModLoader/releases/download/v2026.08.3.0/tModLoader.zip' native-probe/tmodloader.zip 61e865f3702b12ce4a26c5a90b9de99a12c65ffc228455eb3390ce54af1eab15
unzip -q native-probe/tmodloader.zip -d native-probe/tmodloader
# Only logs are uploaded. Proprietary server payloads stay in this disposable runner.
exit "$result"
