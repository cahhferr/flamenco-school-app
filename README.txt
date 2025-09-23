Projeto pronto para publicação no Streamlit Community Cloud.

1) Suba estes arquivos para um repositório GitHub (app.py, requirements.txt, .streamlit/secrets.example.toml).
2) No Streamlit Cloud, em Settings > Secrets, cole o conteúdo de secrets.example.toml (ajustando seus dados).
3) Em [app] defina spreadsheet_id com o ID da sua Google Planilha (a sequência no link entre /d/ e /edit).
4) Compartilhe a planilha com o client_email do Service Account (Editor).
5) Faça o deploy e use o botão "Criar/Sincronizar abas..." na interface para criar as abas padrão.