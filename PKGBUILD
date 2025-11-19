# Maintainer: Tim Jefferies <tim.jefferies@gmail.com>
pkgname=aegis-cli
pkgver=0.1.0
pkgrel=1
pkgdesc="A command-line interface (CLI) tool for viewing Aegis Authenticator TOTP codes, rewritten in Python."
arch=('any')
url="https://github.com/tim-projects/${pkgname}"
license=('GPL3')
depends=('python' 'python-pyotp' 'python-cryptography')
makedepends=('python')
source=("${pkgname}::git+${url}.git#branch=main")
sha256sums=('SKIP')

build() {
  true
}

package() {
  cd "${srcdir}/${pkgname}"
  # Install Python source files into site-packages
  install -d "${pkgdir}/usr/lib/python3.13/site-packages/aegis_cli"
  install -m 644 "avdu_core.py" "${pkgdir}/usr/lib/python3.13/site-packages/aegis_cli/"
  install -m 644 "cli.py" "${pkgdir}/usr/lib/python3.13/site-packages/aegis_cli/"
  install -m 644 "otp.py" "${pkgdir}/usr/lib/python3.13/site-packages/aegis_cli/"
  install -m 644 "vault.py" "${pkgdir}/usr/lib/python3.13/site-packages/aegis_cli/"

  # Create the executable wrapper script
  install -d "${pkgdir}/usr/bin"
  cat > "${pkgdir}/usr/bin/aegis-cli" << EOF
#!/bin/bash
python3 -m aegis_cli.cli "$@"
EOF
  chmod 755 "${pkgdir}/usr/bin/aegis-cli"

  # Install license
  install -d "${pkgdir}/usr/share/licenses/${pkgname}"
  install -m 644 "LICENSE" "${pkgdir}/usr/share/licenses/${pkgname}/"
}
