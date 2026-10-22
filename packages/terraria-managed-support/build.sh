TERMUX_PKG_HOMEPAGE=https://github.com/MonoMod/MonoMod
TERMUX_PKG_DESCRIPTION="Application-local Bionic MonoMod support for Terraria server launchers"
TERMUX_PKG_LICENSE="MIT, Apache-2.0"
TERMUX_PKG_LICENSE_FILE="LICENSE, external/iced/LICENSE.txt"
TERMUX_PKG_MAINTAINER="josephluopooh"
TERMUX_PKG_VERSION="1.3.2"
TERMUX_PKG_SRCURL=("https://codeload.github.com/MonoMod/MonoMod/tar.gz/1fea03f95352a70268a069e68b232c8be0c7f296"
    "https://codeload.github.com/icedland/iced/tar.gz/c50f29b7bc305696895c075f3fc7719751426b12")
TERMUX_PKG_SHA256=(1154cfaa8986aa04e7d18432172402f7fc8a84d8bf3e66f7f7357db359f1bc59
    c5f2473db51e3ab6c48a2c4dcf099e5b29f16ef83b251c46868cb68025b1d7e7)
TERMUX_PKG_DEPENDS="dotnet-host"
TERMUX_PKG_EXCLUDED_ARCHES="arm i686 x86_64"
TERMUX_PKG_BUILD_IN_SRC=true
TERMUX_PKG_AUTO_UPDATE=false

termux_step_pre_configure() {
    mkdir -p external/iced "$TERMUX_PKG_TMPDIR/sdk"
    cp -a iced-c50f29b7bc305696895c075f3fc7719751426b12/. external/iced/
    python3 "$TERMUX_PKG_BUILDER_DIR/port.py" "$TERMUX_PKG_SRCDIR"
    curl --fail --location --retry 3 'https://builds.dotnet.microsoft.com/dotnet/Sdk/9.0.319/dotnet-sdk-9.0.319-linux-x64.tar.gz' -o "$TERMUX_PKG_TMPDIR/sdk.tar.gz"
    printf '%s  %s\n' ed080b81dd2cca56a453c939468b0061a60a083a87eaf21e035794cd28a14fc00faf52d96a4e4116f3cc1de40e6289cd0f08a8fd478d49e4dc4f28570e2f602c "$TERMUX_PKG_TMPDIR/sdk.tar.gz" | sha512sum -c -
    tar -xf "$TERMUX_PKG_TMPDIR/sdk.tar.gz" -C "$TERMUX_PKG_TMPDIR/sdk"
    export DOTNET_ROOT="$TERMUX_PKG_TMPDIR/sdk" DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
    export NUGET_PACKAGES="$TERMUX_PKG_TMPDIR/nuget"
    export PATH="$DOTNET_ROOT:$PATH"
}
termux_step_configure() { :; }
termux_step_make() {
    dotnet build src/MonoMod.Core/MonoMod.Core.csproj -c Release -f net8.0 \
        -p:RestoreLockedMode=false -p:MMBannedApis=false -p:EnableNETAnalyzers=false -p:DoNotAddSuffix=true
    # Keep this project outside MonoMod's tree so it cannot inherit MonoMod's
    # Directory.Build.props/targets, multi-targeting or locked-restore settings.
    local support_src="$TERMUX_PKG_TMPDIR/support-src"
    mkdir -p "$support_src"
    cat > "$support_src/managed-patch.csproj" <<'XML'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <UseAppHost>false</UseAppHost>
    <SelfContained>false</SelfContained>
    <RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Mono.Cecil" Version="[0.11.6]" />
    <PackageReference Include="MonoMod.RuntimeDetour" Version="[25.3.2]" />
    <PackageReference Include="MonoMod.Core" Version="[1.3.2]" />
    <PackageReference Include="MonoMod.Utils" Version="[25.0.10]" />
    <PackageReference Include="MonoMod.Backports" Version="[1.1.2]" />
    <PackageReference Include="MonoMod.ILHelpers" Version="[1.1.0]" />
  </ItemGroup>
</Project>
XML
    cp "$TERMUX_PKG_BUILDER_DIR/managed-patch.cs" "$support_src/Program.cs"
    dotnet publish "$support_src/managed-patch.csproj" -c Release -o "$TERMUX_PKG_TMPDIR/support"
    local core
    core=$(find artifacts/bin/MonoMod.Core -path '*net8.0/MonoMod.Core.dll' -print -quit)
    test -n "$core"
    cp "$core" "$TERMUX_PKG_TMPDIR/support/MonoMod.Core.dll"
    "$CC" $CFLAGS -shared -fPIC -Wl,-z,max-page-size=16384 "$TERMUX_PKG_BUILDER_DIR/cache.c" -o "$TERMUX_PKG_TMPDIR/support/libmonomod-bionic.so" $LDFLAGS
}
termux_step_make_install() {
    local private="$TERMUX_PREFIX/lib/terraria-managed-support"
    local doc="$TERMUX_PREFIX/share/doc/terraria-managed-support"
    mkdir -p "$private" "$doc"
    cp -a "$TERMUX_PKG_TMPDIR/support/." "$private/"
    install -m600 "$TERMUX_PKG_BUILDER_DIR/managed_setup.py" "$private/managed_setup.py"
    install -m600 "$TERMUX_PKG_BUILDER_DIR/README.md" "$doc/README.md"
    # Inspect the published runtime closure, not all build-only NuGet tooling.
    # A license expression alone is insufficient: retain the actual copyright
    # and permission text from embedded notices or exact upstream revisions.
    python3 "$TERMUX_PKG_BUILDER_DIR/notices.py" "$NUGET_PACKAGES" \
        "$TERMUX_PKG_TMPDIR/support/managed-patch.deps.json" "$doc/dependency-licenses"
    cp "$TERMUX_PKG_TMPDIR/support-src/packages.lock.json" "$doc/nuget-packages.lock.json"
    install -m600 "$TERMUX_SCRIPTDIR/packages/termux-licenses/LICENSES/Apache-2.0.txt" "$doc/LICENSE-setup-Apache-2.0.txt"
    mkdir -p "$doc/changes"
    cp "$TERMUX_PKG_BUILDER_DIR/"{port.py,cache.c,managed-patch.cs} "$doc/changes/"
}
