#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${GITHUB_REPOSITORY:?}" "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${GITHUB_RUN_ATTEMPT:?}"
tag="repo-aarch64-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
signed=false
export GNUPGHOME
GNUPGHOME=$(mktemp -d)
chmod 700 "$GNUPGHOME"
trap 'gpgconf --kill gpg-agent || true; rm -rf "$GNUPGHOME"' EXIT
if [[ -n ${REPO_SIGNING_KEY:-} ]]; then
    test -s keys/repository.asc && test -s keys/fingerprint
    fingerprint=$(tr -d '[:space:]' < keys/fingerprint)
    [[ $fingerprint =~ ^[A-F0-9]{40}$ ]]
    actual=$(gpg --batch --with-colons --show-keys keys/repository.asc | awk -F: '$1 == "fpr" {print $10; exit}')
    [[ $actual == "$fingerprint" ]] || { echo 'Public key fingerprint mismatch'; exit 1; }
    gpg --batch --import keys/repository.asc
    printf '%s' "$REPO_SIGNING_KEY" | gpg --batch --import
    unset REPO_SIGNING_KEY
    printf '%s' "${REPO_SIGNING_PASSPHRASE:-}" > "$GNUPGHOME/passphrase"
    chmod 600 "$GNUPGHOME/passphrase"
    unset REPO_SIGNING_PASSPHRASE
    gpg --batch --list-secret-keys "$fingerprint" >/dev/null
    signed=true
    cp keys/repository.asc dist/repository-key.asc
    cp keys/fingerprint dist/repository-key-fingerprint.txt
    # repo-add embeds these signatures in the sync database.
    for package in dist/*.pkg.tar.xz; do
        gpg --batch --yes --pinentry-mode loopback --passphrase-file "$GNUPGHOME/passphrase" --local-user "$fingerprint" --detach-sign "$package"
    done
fi
python3 scripts/repository.py dist
# All previously published bytes remain downloadable after the latest pointer moves.
# The current database indexes the complete package manifest from this build.
# Fail closed on API errors other than a first-publication 404.
mkdir -p previous
if gh api "repos/$GITHUB_REPOSITORY/releases/latest" > previous/release.json 2> previous/api-error; then
    previous_tag=$(jq -r .tag_name previous/release.json)
    gh release download "$previous_tag" --repo "$GITHUB_REPOSITORY" --dir previous \
        --pattern '*.pkg.tar.xz' --pattern '*.pkg.tar.xz.sig'
    for package in previous/*.pkg.tar.xz; do
        $signed || { echo 'Refusing unsigned publication over an existing signed repository'; exit 1; }
        gpg --batch --verify "$package.sig" "$package"
        target="dist/$(basename "$package")"
        if [[ -e $target ]]; then
            cmp "$package" "$target"
        else
            cp "$package" "$package.sig" dist/
        fi
    done
elif ! grep -q 'HTTP 404' previous/api-error; then
    cat previous/api-error >&2
    exit 1
fi
tar -czf dist/build-evidence.tar.gz -C dist evidence
rm -rf dist/evidence
if $signed; then
    for file in dist/termux_repo-aarch64.db{,.tar.gz} dist/termux_repo-aarch64.files{,.tar.gz} dist/repository-index.json dist/build-evidence.tar.gz; do
        gpg --batch --yes --pinentry-mode loopback --passphrase-file "$GNUPGHOME/passphrase" --local-user "$fingerprint" --detach-sign "$file"
    done
    for source in dist/*-source.tar.gz; do
        [[ -f $source ]] || continue
        gpg --batch --yes --pinentry-mode loopback --passphrase-file "$GNUPGHOME/passphrase" --local-user "$fingerprint" --detach-sign "$source"
    done
fi
(cd dist && find . -maxdepth 1 -type f ! -name SHA256SUMS ! -name SHA256SUMS.sig -printf '%f\n' | LC_ALL=C sort | xargs sha256sum) > /tmp/repository-SHA256SUMS
mv /tmp/repository-SHA256SUMS dist/SHA256SUMS
if $signed; then
    gpg --batch --yes --pinentry-mode loopback --passphrase-file "$GNUPGHOME/passphrase" --local-user "$fingerprint" --detach-sign dist/SHA256SUMS
    for sig in dist/*.sig; do gpg --batch --verify "$sig" "${sig%.sig}"; done
    status='Signed Pacman repository; aarch64 / Android 7+ / com.termux Bionic prefix.'
else
    status='UNSIGNED BUILD CANDIDATE. Signing key setup is pending. Do not disable signature checks to install. This prerelease is not promoted to the repository endpoint.'
fi
cat > /tmp/release-notes.md <<EOF_NOTES
$status

Source commit: $GITHUB_SHA
Build: https://github.com/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID

Includes native Pacman packages, sync and file databases, SHA256SUMS, repository-index.json, and build-evidence.tar.gz. WeeChat is named weechat-cjson and conflicts with official weechat because their installed files overlap. See the README at this commit for installation, dependency, signing, and update instructions.
EOF_NOTES
# Fully upload and verify a draft before exposing the new snapshot.
gh release create "$tag" --repo "$GITHUB_REPOSITORY" --target "$GITHUB_SHA" --draft \
    --title "Termux Pacman aarch64 · $GITHUB_RUN_ID.$GITHUB_RUN_ATTEMPT" --notes-file /tmp/release-notes.md
gh release upload "$tag" dist/* --repo "$GITHUB_REPOSITORY"
mkdir -p /tmp/release-verify
gh release download "$tag" --repo "$GITHUB_REPOSITORY" --dir /tmp/release-verify
(cd /tmp/release-verify && sha256sum -c SHA256SUMS)
if $signed; then
    gpg --verify /tmp/release-verify/SHA256SUMS.sig /tmp/release-verify/SHA256SUMS
    gh release edit "$tag" --repo "$GITHUB_REPOSITORY" --draft=false --prerelease=false --latest
else
    gh release edit "$tag" --repo "$GITHUB_REPOSITORY" --draft=false --prerelease --latest=false
fi
printf 'Release: https://github.com/%s/releases/tag/%s\n' "$GITHUB_REPOSITORY" "$tag" >> "$GITHUB_STEP_SUMMARY"
