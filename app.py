import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound
from gspread.utils import rowcol_to_a1
from datetime import datetime
from dateutil import tz
import uuid
import time

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

st.set_page_config(page_title="Escola de Flamenco", page_icon="💃", layout="wide")

def now_sp():
    return datetime.now(tz=tz.gettz("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M:%S")

@st.cache_resource
def get_gspread_client():
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=SCOPES)
    return gspread.authorize(creds)

def open_spreadsheet():
    gc = get_gspread_client()
    spreadsheet_id = st.secrets.get("app", {}).get("spreadsheet_id", "").strip()
    if not spreadsheet_id:
        spreadsheet_id = st.session_state.get("spreadsheet_id_input", "").strip()
    if not spreadsheet_id:
        st.stop()
    try:
        sh = gc.open_by_key(spreadsheet_id)
        return sh
    except Exception as e:
        st.error(f"Erro ao abrir a planilha pelo ID: {e}")
        st.stop()

def ensure_worksheet(sh, title, headers):
    try:
        ws = sh.worksheet(title)
        # Se não houver cabeçalhos, escrever
        first_row = ws.row_values(1)
        if not first_row:
            ws.append_row(headers, value_input_option="RAW")
        return ws
    except WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=1000, cols=max(10, len(headers)))
        ws.append_row(headers, value_input_option="RAW")
        return ws

def get_headers(ws):
    return ws.row_values(1)

def read_df(ws):
    rows = ws.get_all_records()
    df = pd.DataFrame(rows)
    return df

def find_row_by_id(ws, record_id):
    data = ws.get_all_records()
    for idx, row in enumerate(data, start=2):  # 2 = primeira linha de dados
        if str(row.get("id")) == str(record_id):
            return idx
    return None

def append_dict(ws, row_dict):
    headers = get_headers(ws)
    values = [row_dict.get(h, "") for h in headers]
    ws.append_row(values, value_input_option="USER_ENTERED")

def update_by_id(ws, record_id, new_values):
    headers = get_headers(ws)
    row_number = find_row_by_id(ws, record_id)
    if not row_number:
        raise ValueError("ID não encontrado.")
    current = {h: ws.cell(row_number, i+1).value for i, h in enumerate(headers)}
    current.update(new_values)
    values = [current.get(h, "") for h in headers]
    rng = f"A{row_number}:{rowcol_to_a1(row_number, len(headers))}"
    ws.update(rng, [values], value_input_option="USER_ENTERED")

def delete_by_id(ws, record_id):
    row_number = find_row_by_id(ws, record_id)
    if not row_number:
        raise ValueError("ID não encontrado.")
    ws.delete_rows(row_number)

def alunos_page(sh):
    ws = ensure_worksheet(sh, "Alunos", ["id","nome","documento","telefone","email","data_cadastro"])
    st.subheader("Cadastro de Alunos")
    with st.form("form_aluno", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome completo")
            documento = st.text_input("Documento (CPF/ID)")
            telefone = st.text_input("Telefone/WhatsApp")
        with col2:
            email = st.text_input("E-mail")
            aluno_id_edicao = st.text_input("ID para editar (opcional)")
        submitted = st.form_submit_button("Salvar")
    if submitted:
        try:
            if aluno_id_edicao.strip():
                update_by_id(ws, aluno_id_edicao.strip(), {
                    "nome": nome, "documento": documento, "telefone": telefone, "email": email
                })
                st.success("Aluno atualizado.")
            else:
                novo = {
                    "id": str(uuid.uuid4())[:8],
                    "nome": nome,
                    "documento": documento,
                    "telefone": telefone,
                    "email": email,
                    "data_cadastro": now_sp(),
                }
                append_dict(ws, novo)
                st.success("Aluno cadastrado.")
            time.sleep(0.5)
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
    st.divider()
    st.caption("Lista de alunos")
    try:
        df = read_df(ws)
        if df.empty:
            st.info("Nenhum aluno cadastrado ainda.")
        else:
            st.dataframe(df, use_container_width=True)
            with st.expander("Editar/Excluir"):
                id_editar = st.text_input("ID (para editar ou excluir)")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Excluir por ID"):
                        try:
                            delete_by_id(ws, id_editar.strip())
                            st.success("Excluído.")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir: {e}")
                with c2:
                    st.info("Para editar, informe o ID no formulário acima e altere os campos.")
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")

def turmas_page(sh):
    ws = ensure_worksheet(sh, "Turmas", ["id","nome","nivel","dia_hora","professora","vagas"])
    st.subheader("Cadastro de Turmas")
    with st.form("form_turma", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome da turma")
            nivel = st.text_input("Nível (Iniciante, Intermediário, Avançado)")
            dia_hora = st.text_input("Dia/Hora (ex.: Terças 19h)")
        with col2:
            professora = st.text_input("Professora")
            vagas = st.number_input("Vagas", min_value=1, step=1, value=15)
            turma_id_edicao = st.text_input("ID para editar (opcional)")
        submitted = st.form_submit_button("Salvar")
    if submitted:
        try:
            if turma_id_edicao.strip():
                update_by_id(ws, turma_id_edicao.strip(), {
                    "nome": nome, "nivel": nivel, "dia_hora": dia_hora, "professora": professora, "vagas": int(vagas)
                })
                st.success("Turma atualizada.")
            else:
                novo = {
                    "id": str(uuid.uuid4())[:8],
                    "nome": nome,
                    "nivel": nivel,
                    "dia_hora": dia_hora,
                    "professora": professora,
                    "vagas": int(vagas)
                }
                append_dict(ws, novo)
                st.success("Turma criada.")
            time.sleep(0.5)
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
    st.divider()
    df = read_df(ws)
    if df.empty:
        st.info("Nenhuma turma cadastrada ainda.")
    else:
        st.dataframe(df, use_container_width=True)

def matriculas_page(sh):
    ws_m = ensure_worksheet(sh, "Matriculas", ["id","aluno_id","turma_id","data_inicio","status"])
    ws_a = ensure_worksheet(sh, "Alunos", ["id","nome","documento","telefone","email","data_cadastro"])
    ws_t = ensure_worksheet(sh, "Turmas", ["id","nome","nivel","dia_hora","professora","vagas"])
    st.subheader("Matrículas")
    df_a = read_df(ws_a)
    df_t = read_df(ws_t)
    alunos_opts = []
    turmas_opts = []
    if not df_a.empty:
        alunos_opts = [(f'{r["nome"]} ({r["id"]})', r["id"]) for _, r in df_a.iterrows()]
    if not df_t.empty:
        turmas_opts = [(f'{r["nome"]} - {r["dia_hora"]} ({r["id"]})', r["id"]) for _, r in df_t.iterrows()]
    with st.form("form_matricula", clear_on_submit=False):
        aluno_sel = st.selectbox("Aluno", alunos_opts, format_func=lambda x: x[0] if isinstance(x, tuple) else x) if alunos_opts else None
        turma_sel = st.selectbox("Turma", turmas_opts, format_func=lambda x: x[0] if isinstance(x, tuple) else x) if turmas_opts else None
        data_inicio = st.date_input("Data de início")
        status = st.selectbox("Status", ["ativa","trancada","cancelada","concluida"])
        mid = st.text_input("ID para editar (opcional)")
        submitted = st.form_submit_button("Salvar")
    if submitted:
        try:
            if not alunos_opts or not turmas_opts:
                st.error("Cadastre Alunos e Turmas primeiro.")
            else:
                aluno_id = aluno_sel[1]
                turma_id = turma_sel[1]
                if mid.strip():
                    update_by_id(ws_m, mid.strip(), {
                        "aluno_id": aluno_id,
                        "turma_id": turma_id,
                        "data_inicio": str(data_inicio),
                        "status": status
                    })
                    st.success("Matrícula atualizada.")
                else:
                    novo = {
                        "id": str(uuid.uuid4())[:8],
                        "aluno_id": aluno_id,
                        "turma_id": turma_id,
                        "data_inicio": str(data_inicio),
                        "status": status
                    }
                    append_dict(ws_m, novo)
                    st.success("Matrícula criada.")
                time.sleep(0.5)
                st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
    st.divider()
    df = read_df(ws_m)
    if df.empty:
        st.info("Nenhuma matrícula cadastrada.")
    else:
        st.dataframe(df, use_container_width=True)
        with st.expander("Excluir matrícula"):
            did = st.text_input("ID da matrícula para excluir")
            if st.button("Excluir"):
                try:
                    delete_by_id(ws_m, did.strip())
                    st.success("Excluída.")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")

def pagamentos_page(sh):
    ws_p = ensure_worksheet(sh, "Pagamentos", ["id","aluno_id","competencia","valor","status","data_pagto"])
    ws_a = ensure_worksheet(sh, "Alunos", ["id","nome","documento","telefone","email","data_cadastro"])
    st.subheader("Pagamentos")
    df_a = read_df(ws_a)
    alunos_opts = [(f'{r["nome"]} ({r["id"]})', r["id"]) for _, r in df_a.iterrows()] if not df_a.empty else []
    with st.form("form_pagto", clear_on_submit=False):
        aluno_sel = st.selectbox("Aluno", alunos_opts, format_func=lambda x: x[0] if isinstance(x, tuple) else x) if alunos_opts else None
        competencia = st.text_input("Competência (AAAA-MM)", placeholder="2025-09")
        valor = st.number_input("Valor", min_value=0.0, step=10.0)
        status = st.selectbox("Status", ["pago","pendente","isento"])
        data_pagto = st.date_input("Data de pagamento (se pago)")
        pid = st.text_input("ID para editar (opcional)")
        submitted = st.form_submit_button("Salvar")
    if submitted:
        try:
            if not alunos_opts:
                st.error("Cadastre Alunos primeiro.")
            else:
                aluno_id = aluno_sel[1]
                if pid.strip():
                    update_by_id(ws_p, pid.strip(), {
                        "aluno_id": aluno_id,
                        "competencia": competencia,
                        "valor": float(valor),
                        "status": status,
                        "data_pagto": str(data_pagto) if status == "pago" else ""
                    })
                    st.success("Pagamento atualizado.")
                else:
                    novo = {
                        "id": str(uuid.uuid4())[:8],
                        "aluno_id": aluno_id,
                        "competencia": competencia,
                        "valor": float(valor),
                        "status": status,
                        "data_pagto": str(data_pagto) if status == "pago" else ""
                    }
                    append_dict(ws_p, novo)
                    st.success("Pagamento lançado.")
                time.sleep(0.5)
                st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
    st.divider()
    df = read_df(ws_p)
    if df.empty:
        st.info("Nenhum pagamento lançado.")
    else:
        st.dataframe(df, use_container_width=True)
        with st.expander("Excluir pagamento"):
            did = st.text_input("ID do pagamento para excluir")
            if st.button("Excluir"):
                try:
                    delete_by_id(ws_p, did.strip())
                    st.success("Excluído.")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")

def relatorios_page(sh):
    ws_p = ensure_worksheet(sh, "Pagamentos", ["id","aluno_id","competencia","valor","status","data_pagto"])
    ws_a = ensure_worksheet(sh, "Alunos", ["id","nome","documento","telefone","email","data_cadastro"])
    ws_t = ensure_worksheet(sh, "Turmas", ["id","nome","nivel","dia_hora","professora","vagas"])
    ws_m = ensure_worksheet(sh, "Matriculas", ["id","aluno_id","turma_id","data_inicio","status"])

    st.subheader("Relatórios")
    df_p = read_df(ws_p)
    df_a = read_df(ws_a)
    df_t = read_df(ws_t)
    df_m = read_df(ws_m)

    if df_p.empty and df_m.empty:
        st.info("Cadastre matrículas e pagamentos para ver relatórios.")
        return

    st.markdown("Arrecadação por competência (considera pagos)")
    if not df_p.empty:
        df_p["valor"] = pd.to_numeric(df_p.get("valor", 0), errors="coerce").fillna(0.0)
        df_p["status"] = df_p.get("status", "").astype(str)
        df_paid = df_p[df_p["status"] == "pago"]
        if not df_paid.empty:
            agg = df_paid.groupby("competencia", dropna=False)["valor"].sum().reset_index().sort_values("competencia")
            st.dataframe(agg, use_container_width=True)
            st.download_button("Baixar CSV arrecadação", agg.to_csv(index=False).encode("utf-8"), "arrecadacao.csv", "text/csv")
        else:
            st.info("Nenhum pagamento com status 'pago'.")

    st.markdown("Matrículas por turma (ativas)")
    if not df_m.empty and not df_t.empty:
        df_ma = df_m[df_m["status"] == "ativa"].copy()
        if not df_ma.empty:
            counts = df_ma.groupby("turma_id").size().reset_index(name="qtd")
            mapa_turmas = df_t.set_index("id")["nome"].to_dict()
            counts["turma"] = counts["turma_id"].map(mapa_turmas)
            counts = counts[["turma","qtd"]].sort_values("turma")
            st.dataframe(counts, use_container_width=True)

def sidebar_setup():
    st.sidebar.title("Módulos")
    return st.sidebar.radio("Escolha", ["Alunos","Turmas","Matrículas","Pagamentos","Relatórios"])

def main():
    st.title("Sistema da Escola de Flamenco")
    st.caption("Cadastro de alunos, turmas, matrículas e pagamentos usando Google Planilhas.")

    # Entrada do Spreadsheet ID caso não esteja nos secrets
    if "spreadsheet_id_input" not in st.session_state:
        st.session_state["spreadsheet_id_input"] = ""
    sid = st.text_input("Spreadsheet ID (cole aqui se não estiver em Secrets)", value=st.session_state["spreadsheet_id_input"], placeholder="1AbCDeFgHIjk...")
    st.session_state["spreadsheet_id_input"] = sid

    sh = open_spreadsheet()

    # Botão utilitário para criar abas e cabeçalhos, se faltarem
    if st.button("Criar/Sincronizar abas padrão (Alunos, Turmas, Matriculas, Pagamentos)"):
        ensure_worksheet(sh, "Alunos", ["id","nome","documento","telefone","email","data_cadastro"])
        ensure_worksheet(sh, "Turmas", ["id","nome","nivel","dia_hora","professora","vagas"])
        ensure_worksheet(sh, "Matriculas", ["id","aluno_id","turma_id","data_inicio","status"])
        ensure_worksheet(sh, "Pagamentos", ["id","aluno_id","competencia","valor","status","data_pagto"])
        st.success("Abas verificadas/criadas (com cabeçalhos).")

    pagina = sidebar_setup()
    if pagina == "Alunos":
        alunos_page(sh)
    elif pagina == "Turmas":
        turmas_page(sh)
    elif pagina == "Matrículas":
        matriculas_page(sh)
    elif pagina == "Pagamentos":
        pagamentos_page(sh)
    else:
        relatorios_page(sh)

if __name__ == "__main__":
    main()
