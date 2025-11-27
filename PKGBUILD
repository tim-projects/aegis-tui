# Maintainer: Tim Jefferies <tim.jefferies@gmail.com>
pkgname=aegis-tui
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
  cd "${srcdir}"
  # Install Python source files into site-packages
  install -d "${pkgdir}/usr/lib/python3.13/site-packages/aegis_tui"
  install -m 644 "aegis_core.py" "${pkgdir}/usr/lib/python3.13/site-packages/aegis_tui/"
  install -m 644 "aegis-tui.py" "${pkgdir}/usr/lib/python3.13/site-packages/aegis_tui/"
  install -m 644 "otp.py" "${pkgdir}/usr/lib/python3.13/site-packages/aegis_tui/"
  install -m 644 "vault.py" "${pkgdir}/usr/lib/python3.13/site-packages/aegis_tui/"

  # Create the executable wrapper script
  install -d "${pkgdir}/usr/bin"
  cat > "${pkgdir}/usr/bin/aegis-tui" << EOF
#!/bin/bash
python3 -m aegis_tui.aegis-tui "$@"
EOF
  chmod 755 "${pkgdir}/usr/bin/aegis-tui"

  # Install license
  install -d "${pkgdir}/usr/share/licenses/${pkgname}"
  install -m 644 "LICENSE" "${pkgdir}/usr/share/licenses/${pkgname}/"
}
