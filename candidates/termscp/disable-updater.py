from pathlib import Path
p = Path('src/main.rs')
s = p.read_text()
start = s.index('fn run_install_update()')
end = s.index('\n}', start) + 2
s = s[:start] + """fn run_install_update() -> MainResult<()> {
    eprintln!("This installation is managed by Pacman. Run: pacman -Syu");
    Ok(())
}""" + s[end:]
p.write_text(s)
