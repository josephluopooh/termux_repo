"""Application-local Bionic source adaptation of the pinned MonoMod.Core."""
from pathlib import Path
import sys

root = Path(sys.argv[1])
core = root / 'src/MonoMod.Core'
unix = core / 'Interop/Unix.cs'
text = unix.read_text(encoding='utf-8-sig')
text = text.replace('public static unsafe int Errno => *__errno_location();', '''
        [DllImport(LibC, CallingConvention = CallingConvention.Cdecl, EntryPoint = "__errno")]
        private static extern unsafe int* BionicErrno();

        [DllImport(LibC, CallingConvention = CallingConvention.Cdecl, EntryPoint = "getpagesize")]
        public static extern int GetPageSize();

        private static readonly bool IsBionic = RuntimeInformation.RuntimeIdentifier.Contains("bionic");
        public static unsafe int Errno => IsBionic ? *BionicErrno() : *__errno_location();''')
unix.write_text(text)
triple = core / 'Platforms/PlatformTriple.cs'
text = triple.read_text(encoding='utf-8-sig')
text = text.replace('OSKind.Linux => new Systems.LinuxSystem(),', '''OSKind.Linux when global::System.Runtime.InteropServices.RuntimeInformation.RuntimeIdentifier.Contains("bionic")
                    => new Systems.AndroidSystem(),
                OSKind.Linux => new Systems.LinuxSystem(),''')
text = text.replace('OSKind.Android => throw new NotImplementedException(),', 'OSKind.Android => new Systems.AndroidSystem(),')
triple.write_text(text)
linux = core / 'Platforms/Systems/LinuxSystem.cs'
text = linux.read_text(encoding='utf-8-sig').replace('LinuxSystem', 'AndroidSystem').replace('=> OSKind.Linux;', '=> OSKind.Android;')
text = text.replace('(nint)Unix.Sysconf(Unix.SysconfName.PageSize)', '(nint)Unix.GetPageSize()')
text = text.replace('data.CopyTo(target);', '''data.CopyTo(target);
            if (patchKind == PatchTargetKind.Executable)
                ClearCache(patchTarget, patchTarget + data.Length);''')
text = text.replace('private void RoundToPageBoundary', '''[System.Runtime.InteropServices.DllImport("monomod-bionic", EntryPoint = "mm_clear_cache")]
        private static extern void ClearCache(IntPtr start, IntPtr end);

        private void RoundToPageBoundary''')
text = text.replace('private static ReadOnlySpan<byte> NEHTempl => "/tmp/mm-exhelper.so.XXXXXX"u8;', '''private static ReadOnlySpan<byte> NEHTempl => System.Text.Encoding.UTF8.GetBytes(
            System.IO.Path.Combine(System.IO.Path.GetTempPath(), "mm-exhelper.so.XXXXXX"));''')
(core / 'Platforms/Systems/AndroidSystem.cs').write_text(text)
