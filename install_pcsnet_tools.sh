#!/bin/bash
#----------------------------------------------------
# Name:    PCSNet Web Tools Installation Script 
# Author:  Kang Ali
# Version: v1.0  
# Date:    2025-05-23
#----------------------------------------------------

# --- Konfigurasi Tools ---
# Direktori dasar tempat tools seperti Sublist3r akan diinstal.
TOOLS_BASE_DIR="/opt/pcsnet-web-tools"
SUBLIST3R_REPO="https://github.com/aboul3la/Sublist3r.git"
SUBLIST3R_DIR="${TOOLS_BASE_DIR}/Sublist3r"

# --- Fungsi Logging ---
log_info() {
    echo -e "\e[32m[INFO]\e[0m $1"
}

log_warn() {
    echo -e "\e[33m[PERINGATAN]\e[0m $1"
}

log_error() {
    echo -e "\e[31m[ERROR]\e[0m $1"
    exit 1
}

# --- Cek Hak Akses Root ---
if [[ $EUID -ne 0 ]]; then
   log_error "Skrip ini harus dijalankan dengan hak akses root (gunakan sudo)."
fi

log_info "Memulai instalasi tools keamanan untuk fitur 'Tools Scanning' di Gemini Chatbot..."

# --- Update Paket Sistem ---
log_info "Memperbarui daftar paket sistem..."
sudo apt-get update -q || log_error "Gagal memperbarui daftar paket."

# --- Instal Prerequisit Sistem dan Tools Keamanan ---
log_info "Menginstal dependensi sistem dan tools keamanan..."
sudo apt-get install -y \
    perl perl-modules libnet-ssleay-perl libwhisker2-perl \
    wget python3-pip libssl-dev libxml2-dev libxslt1-dev libyaml-dev libsqlite3-dev \
    libpcre3 libpcre3-dev libidn11-dev openssl git \
    build-essential libffi-dev rubygems-integration ruby-dev ruby-full \
    sgml-base xml-core nmap wafw00f whatweb sqlmap whois traceroute curl \
    slowhttptest python3-venv \
    || log_error "Gagal menginstal dependensi sistem dan tools."

log_info "Dependensi sistem dan tools berhasil diinstal."

# --- Instal Ruby Gems (Termasuk dependensi spesifik untuk XSpear) ---
log_info "Memperbarui RubyGems dan menginstal dependensi Ruby gem..."
gem install --no-document rubygems-update # Update rubygems itu sendiri
update_rubygems # Jalankan update
gem install --no-document selenium-webdriver -v 3.142.7 || log_warn "Gagal menginstal selenium-webdriver. Lanjutkan instalasi tools lain."
gem install --no-document io-console -v 0.5.9 || log_warn "Gagal menginstal io-console. Lanjutkan instalasi tools lain."
gem install --no-document reline -v 0.3.1 || log_warn "Gagal menginstal reline. Lanjutkan instalasi tools lain."
gem install --no-document highline -v 2.1.0 || log_warn "Gagal menginstal highline. Lanjutkan instalasi tools lain."
# Instal XSpear (tanpa versi spesifik, ambil yang terbaru kompatibel)
gem install --no-document XSpear || log_warn "Gagal menginstal XSpear. Pastikan Ruby dan RubyGems terinstal dengan benar. Lanjutkan instalasi tools lain."
export LC_ALL="en_US.UTF-8" # Set environment variables for gem
export LC_CTYPE="en_US.UTF-8"

# --- Instal Sublist3r (dari GitHub) ---
log_info "Mengkloning dan menginstal Sublist3r dari GitHub..."
mkdir -p "${TOOLS_BASE_DIR}" || log_error "Gagal membuat direktori tools dasar: ${TOOLS_BASE_DIR}."
if [ -d "$SUBLIST3R_DIR" ]; then
    log_info "Direktori Sublist3r sudah ada (${SUBLIST3R_DIR}), melakukan update."
    cd "$SUBLIST3R_DIR"
    git pull || log_warn "Gagal memperbarui Sublist3r. Lanjutkan instalasi tools lain."
else
    git clone "$SUBLIST3R_REPO" "$SUBLIST3R_DIR" || log_error "Gagal mengkloning Sublist3r."
fi
cd "$SUBLIST3R_DIR" || log_error "Gagal masuk ke direktori Sublist3r."
python3 -m pip install --upgrade pip || log_warn "Gagal mengupgrade pip untuk Python 3."
pip install -r requirements.txt || log_warn "Gagal menginstal dependensi Sublist3r dengan pip (Python 3). Sublist3r mungkin memerlukan modifikasi agar kompatibel penuh dengan Python 3. Lanjutkan instalasi tools lain."

log_info "Semua tools keamanan yang diperlukan telah diinstal."

# --- Peringatan Konfigurasi Sudoers untuk Nmap (Opsional dan Hati-hati!) ---
log_warn "======================================================================="
log_warn "PERHATIAN PENTING UNTUK NMAP EXTENSIVE SCAN:"
log_warn "Untuk NMAP Extensive Scan (yang menggunakan 'sudo' di aplikasi Flask),"
log_warn "Anda mungkin perlu mengkonfigurasi sudoers secara manual untuk user yang"
log_warn "menjalankan aplikasi Flask (misalnya 'www-data' jika menggunakan Gunicorn/Systemd,"
log_warn "atau user Anda sendiri jika menjalankan langsung) agar bisa menjalankan NMAP tanpa password."
log_warn "Contoh (buat file baru di /etc/sudoers.d/):"
log_warn "  echo 'www-data ALL=NOPASSWD: /usr/bin/nmap' | sudo tee /etc/sudoers.d/pcsnet_nmap"
log_warn "  sudo chmod 0440 /etc/sudoers.d/pcsnet_nmap"
log_warn "Risiko Keamanan: Memungkinkan user non-root menjalankan perintah dengan sudo tanpa password"
log_warn "                 memiliki RISIKO KEAMANAN yang signifikan. Lakukan dengan sangat hati-hati!"
log_warn "======================================================================="
log_warn "Instalasi tools selesai. Sekarang Anda bisa menjalankan aplikasi Flask Gemini Chatbot."
log_warn "Pastikan SUBLIST3R_PATH di app.py Flask Anda sesuai dengan: ${SUBLIST3R_DIR}/sublist3r.py"

exit 0
