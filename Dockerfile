# Gunakan base image Python resmi
FROM python:3.10-slim-buster

# Atur direktori kerja di dalam container
WORKDIR /app

# Instal dependensi sistem yang diperlukan untuk tools scanning
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    perl libnet-ssleay-perl libwhisker2-perl \
    wget python3-pip libssl-dev libxml2-dev libxslt1-dev libyaml-dev libsqlite3-dev \
    libpcre3 libpcre3-dev libidn11-dev openssl git \
    build-essential libffi-dev rubygems-integration ruby-dev ruby-full \
    sgml-base xml-core nmap wafw00f whatweb sqlmap whois traceroute curl \
    slowhttptest \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Instal Ruby Gems
# Instal selenium-webdriver via Ruby Gem (versi yang kompatibel dengan Ruby 2.5.0)
RUN gem install selenium-webdriver -v 3.142.7
# Instal dependensi io-console versi lama yang kompatibel dengan Ruby 2.5.0
RUN gem install io-console -v 0.5.9
# Instal dependensi reline versi lama yang kompatibel dengan Ruby 2.5.0
RUN gem install reline -v 0.3.1
# Instal dependensi highline versi lama yang kompatibel dengan Ruby 2.5.0 (ditambahkan)
RUN gem install highline -v 2.1.0
# Instal XSpear via Ruby Gem (tanpa versi spesifik, ambil yang terbaru kompatibel)
RUN gem install XSpear
ENV LC_ALL="en_US.UTF-8"
ENV LC_CTYPE="en_US.UTF-8"

# Kloning dan instal Sublist3r
RUN mkdir -p /app/tools && \
    git clone https://github.com/aboul3la/Sublist3r.git /app/tools/Sublist3r && \
    pip install --no-cache-dir -r /app/tools/Sublist3r/requirements.txt

COPY . /app

# Instal dependensi Python aplikasi Flask
RUN pip install --no-cache-dir -r requirements.txt

# Port
EXPOSE 1337

# Perintah untuk menjalankan aplikasi menggunakan Gunicorn (disarankan untuk produksi)
# CMD ["gunicorn", "-b", "0.0.0.0:1337", "app:app"]
# Atau untuk pengembangan, jalankan langsung app.py
CMD ["python3", "app.py"]
