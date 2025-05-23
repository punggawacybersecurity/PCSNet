#!/bin/bash

set -e

echo "Memulai instalasi Docker dan Docker Compose..."

# Uninstall Docker versi lama
echo "Menghapus instalasi Docker lama (jika ada)..."
sudo apt-get remove -y docker docker-engine docker.io containerd runc || true

# Update dan instal dependensi
echo "Mengupdate paket dan menginstal dependensi..."
sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Tambahkan Docker GPG key
echo "Menambahkan GPG key Docker..."
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Tambahkan repository Docker
echo "Menambahkan repository Docker..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update lagi dan install Docker terbaru
echo "Menginstal Docker Engine..."
sudo apt-get update
sudo apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

# Tambahkan user saat ini ke grup docker
echo "Menambahkan user '$USER' ke grup docker (agar bisa jalankan tanpa sudo)..."
sudo usermod -aG docker $USER

# Tes versi
echo "Docker versi:"
docker --version
echo "Docker Compose versi:"
docker compose version

# Jalankan hello-world sebagai tes
echo "Menjalankan container uji (hello-world)..."
docker run hello-world || true

echo ""
echo "✅ Instalasi selesai!"
