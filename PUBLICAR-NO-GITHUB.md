# Publicar no GitHub com segurança

Este guia evita vazar segredos **antes** do primeiro `git push`.

## O que vai para o GitHub (seguro)

| Arquivo / pasta | Motivo |
|-----------------|--------|
| `docker-compose.yml`, Dockerfiles, `*_api.py` | Código sem segredos |
| `.env.example` | Apenas placeholders |
| `n8n-ia-workflow.example.json` | Workflow **sem** URLs de webhook reais |
| `.gitignore` | Impede commit acidental |

## O que **nunca** deve ir para o GitHub

| Item | Por quê |
|------|---------|
| `.env` | E-mail, telefone, IDs reais |
| Pasta `data/` inteira | Banco n8n + chave de criptografia + OAuth |
| `n8n-ia-workflow.json` | Contém os webhooks de produção |
| `ollama_data/` | Chave privada e modelos locais |
| `*.tar`, `kokoro-v1.0.onnx`, `voices-v1.0.bin` | Arquivos grandes (build local) |

## Passo a passo (primeira publicação)

### 1. Inicializar o repositório

```powershell
cd "caminho\para\AGIL.AI"
git init
```

### 2. Rodar a verificação

```powershell
.\scripts\verificar-antes-do-push.ps1
```

Só continue se aparecer **OK**.

### 3. Primeiro commit

```powershell
git add .
git status
```

Confira no `git status` que **não** aparecem: `.env`, `data/`, `n8n-ia-workflow.json`.

```powershell
git commit -m "Projeto AGIL.AI — bot IA com n8n, Ollama, Whisper e Kokoro"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/SEU_REPO.git
git push -u origin main
```

### 4. Após clonar em outra máquina

1. `copy .env.example .env` e preencher valores reais  
2. `docker compose up -d`  
3. Abrir n8n → importar `n8n-ia-workflow.example.json`  
4. Reconectar credenciais (Twilio, Gmail, Google, Trello) na UI  
5. **Gerar novo path de webhook** no nó “Webhook Recebe Mensagem Usuário”  
6. Atualizar a URL do webhook no **Twilio** com a nova URL do n8n  

## Webhook: por que há dois arquivos?

- `n8n-ia-workflow.json` → seu fluxo **de produção** (fica só no PC, no `.gitignore`)
- `n8n-ia-workflow.example.json` → versão **pública** com paths substituídos

Quem clonar o repo não terá sua URL secreta do Twilio.

## Opcional: limpar PII local antes de compartilhar o PC

Os logs não vão para o Git, mas você pode apagar localmente:

```powershell
Remove-Item data\n8nEventLog*.log -ErrorAction SilentlyContinue
```

O n8n recria logs novos automaticamente.

## Se algo sensível já tiver ido para o Git por engano

1. Remova do histórico (`git filter-repo` ou GitHub “secret scanning”)  
2. **Rotacione** token Twilio e **reautorize** OAuth (Google, Trello)  
3. Gere **novo** webhook no n8n e atualize o Twilio  
