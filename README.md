# Fluxo CI/CD com Registry Privado e Watchtower

Este documento descreve a infraestrutura de deploy contínuo configurada via Portainer em um servidor Debian.

## Arquitetura e Motivos

1. **Rede Docker Centralizada:** A rede `custom_network` isola a comunicação entre os serviços.
2. **Registry Privado com Basic Auth:** Mantém as imagens localmente com segurança de acesso por usuário e senha (criptografia Bcrypt).
3. **Cloudflare Tunnel:** Expõe o Registry (`seu-dominio-registry.com`) para a internet com SSL automático. O motivo é permitir que o GitHub Actions faça o push das imagens de forma segura, sem precisar abrir portas no roteador/firewall do servidor.
4. **Insecure Registry (Gateway IP):** O Docker foi configurado para aceitar tráfego HTTP no IP `172.18.0.1:5000`. O motivo é forçar o servidor a puxar as imagens internamente (sem passar pela internet ou pelo Cloudflare), evitando erros de DNS e gargalos de rede.
5. **Watchtower:** Automatiza os deploys. Ele monitora atualizações no Registry e recria o container da aplicação automaticamente, utilizando o arquivo de credenciais do sistema operacional host.

---

## 1. Configuração do Docker Daemon (`/etc/docker/daemon.json`)

Libera a comunicação HTTP interna para o download das imagens.

```json
{
  "insecure-registries": ["172.18.0.1:5000"]
}

```

## 2. Stack Base (Infraestrutura)

Sobe o Registry, o Watchtower e o Cloudflare Tunnel. O Watchtower monta o arquivo de credenciais do host para ter permissão de ler as imagens do Registry.

```yaml
version: '3.8'

services:
  registry:
    image: registry:2
    container_name: local-registry
    ports:
      - "5000:5000"
    restart: always
    environment:
      REGISTRY_HTTP_ADDR: 0.0.0.0:5000
      REGISTRY_AUTH: htpasswd
      REGISTRY_AUTH_HTPASSWD_REALM: Registry Realm
      REGISTRY_AUTH_HTPASSWD_PATH: /auth/htpasswd
    volumes:
      - registry_data:/var/lib/registry
      - /opt/registry/auth:/auth:ro
    networks:
      - custom_network

  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    restart: always
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /root/.docker/config.json:/config.json:ro
    command: --interval 30 --cleanup
    networks:
      - custom_network

  cloudflare-tunnel:
    image: cloudflare/cloudflared:latest
    container_name: cloudflare-tunnel
    restart: always
    command: tunnel run --token SEU_TOKEN_AQUI
    networks:
      - custom_network

volumes:
  registry_data:

networks:
  custom_network:
    external: true

```

## 3. GitHub Actions (`.github/workflows/deploy.yml`)

Gera o build do código e envia a imagem para o servidor passando pelo túnel da Cloudflare.

```yaml
name: Build and Push to Local Registry

on:
  push:
    branches:
      - main

jobs:
  build-and-push:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Log in to Local Registry
      uses: docker/login-action@v3
      with:
        registry: seu-dominio-registry.com
        username: ${{ secrets.REGISTRY_USERNAME }}
        password: ${{ secrets.REGISTRY_PASSWORD }}

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
      with:
        driver-opts: |
          image=moby/buildkit:master
          network=host

    - name: Build and Push Image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: seu-dominio-registry.com/hello-world:latest

```

## 4. Stack da Aplicação

Sobe o microsserviço apontando para o IP de gateway do Docker (`172.18.0.1`), garantindo que o pull seja feito pela rota interna do servidor.

```yaml
version: '3.8'

services:
  hello-app:
    image: 172.18.0.1:5000/hello-world:latest
    container_name: hello-app
    ports:
      - "8080:8080"
    restart: always
    networks:
      - custom_network

networks:
  custom_network:
    external: true

```
