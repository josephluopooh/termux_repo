# Repository signing setup

No signing credential is created by the build or publication workflows. The
owner must approve and configure a dedicated OpenPGP signing key before a signed
repository can be published. The current unsigned prerelease path is for reviewing
builds; it never becomes `releases/latest/download`.

Use a key dedicated to this repository, or an approved existing signing subkey.
Keep a secure offline backup and a revocation certificate. Do not commit private
keys or put them in workflow inputs, release assets, logs, or chat.

1. Commit the ASCII-armored **public** key as `keys/repository.asc` and the
   corresponding uppercase full primary fingerprint as `keys/fingerprint`.
   Review the fingerprint through a trusted channel before telling clients to
   trust it. An identity/comment in a key is not proof of ownership.
2. From a trusted workstation with the private key already in its GnuPG keyring,
   store it directly in the repository's Actions secret (the pipe avoids a
   plaintext private-key file):

   ```sh
   gpg --armor --export-secret-keys "$FINGERPRINT" |
     gh secret set REPO_SIGNING_KEY --repo josephluopooh/termux_repo
   ```

   If the export is passphrase-protected, add `REPO_SIGNING_PASSPHRASE` through
   GitHub's encrypted Actions secrets UI or `gh secret set` using its prompt.
   Do not pass the passphrase as a shell argument or commit it.
3. Run the repository workflow again. Signing happens in the publication job
   only, in a temporary GnuPG home removed at exit. The secret must match the
   committed public fingerprint. Packages and both Pacman databases are signed.
4. Confirm the new release is signed, the Actions run is successful, and the
   fingerprint matches. Clients can then follow the README's explicit key trust
   and `SigLevel = Required DatabaseRequired` instructions.

A missing key creates an unsigned prerelease only when no signed repository has
been published. Missing/mismatched signing material after activation fails
publication; it never downgrades the existing signed repository. A signing error
leaves the old `latest` snapshot intact. A failed upload may leave a draft for
manual inspection; rerunning creates a different run-attempt tag.

For key rotation, publish and verify the new fingerprint through a trusted
channel and update clients before promoting packages signed only by the new key.
The carry-forward verification intentionally requires previous package signatures
to verify; a rotation needs an explicit migration design and must not silently
trust an unrelated key or turn off signature checks.
