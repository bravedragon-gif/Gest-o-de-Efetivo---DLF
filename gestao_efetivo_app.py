import json
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import date, datetime
import streamlit as st


# ==========================
#  MODELOS (equivalentes ao types.ts)
# ==========================

class Rank(str, Enum):
    CEL = "CEL"
    TC = "TC"
    MAJ = "MAJ"
    CAP = "CAP"
    TEN_1 = "1º TEN"
    TEN_2 = "2º TEN"
    ST = "ST"
    SGT_1 = "1º SGT"
    SGT_2 = "2º SGT"
    SGT_3 = "3º SGT"
    CB = "CB"
    SD = "SD"
    FCIVIL = "F.CIVIL"


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    USER = "USER"


class LeaveType(str, Enum):
    FERIAS = "FÉRIAS"
    ABONO = "ABONO"
    LTSP = "LTSP"  # Licença Tratamento Saúde Própria
    RESTRICAO = "RESTRIÇÃO"
    LICENCA_ESPECIAL = "LICENÇA ESPECIAL"
    LTIP = "LTIP"
    PRONTO_EMPREGO = "PRONTO EMPREGO"
    EXTRA = "EXTRA"
    REPRESENTACAO = "REPRESENTAÇÃO"
    DISPENSA_RECOMPENSA = "DISPENSA RECOMPENSA"


@dataclass
class Personnel:
    id: str
    ant: int
    grad: str
    quadro: str
    nome: str
    matr: str
    unid: str
    secao: str
    situacao: str
    esc: str
    saldoFerias: int
    saldoAbono: int
    role: str  # ADMIN | MANAGER | USER


@dataclass
class LeaveRecord:
    id: str
    personnel_id: str
    type: str  # LeaveType
    startDate: str  # "YYYY-MM-DD"
    endDate: str    # "YYYY-MM-DD"
    description: str
    createdAt: str  # ISO datetime


@dataclass
class AppState:
    personnel: List[Personnel]
    leaves: List[LeaveRecord]


# ==========================
#  PERSISTÊNCIA EM JSON
# ==========================

DATA_FILE = Path("dados_efetivo.json")


def default_state() -> AppState:
    # Começa vazio, você pode depois criar um script para importar da planilha
    return AppState(personnel=[], leaves=[])


def load_state() -> AppState:
    if not DATA_FILE.exists():
        return default_state()

    with DATA_FILE.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    personnel = [Personnel(**p) for p in raw.get("personnel", [])]
    leaves = [LeaveRecord(**l) for l in raw.get("leaves", [])]
    return AppState(personnel=personnel, leaves=leaves)


def save_state(state: AppState) -> None:
    raw = {
        "personnel": [asdict(p) for p in state.personnel],
        "leaves": [asdict(l) for l in state.leaves],
    }
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)


# ==========================
#  FUNÇÕES AUXILIARES
# ==========================

def generate_id(prefix: str, elements: List[Any]) -> str:
    """
    Gera um ID simples com base na quantidade de elementos existentes.
    Ex: prefix='P' -> P1, P2...
    """
    return f"{prefix}{len(elements) + 1}"


def find_person_by_id(state: AppState, pid: str) -> Optional[Personnel]:
    for p in state.personnel:
        if p.id == pid:
            return p
    return None


def get_leaves_for_person(state: AppState, pid: str) -> List[LeaveRecord]:
    return [l for l in state.leaves if l.personnel_id == pid]


# ==========================
#  INTERFACE STREAMLIT
# ==========================

def page_dashboard(state: AppState):
    st.header("📊 Visão geral (Dashboard simples)")

    total = len(state.personnel)
    em_ferias = 0
    hoje = date.today().isoformat()

    for l in state.leaves:
        if l.type == LeaveType.FERIAS.value and l.startDate <= hoje <= l.endDate:
            em_ferias += 1

    col1, col2 = st.columns(2)
    col1.metric("Total de militares cadastrados", total)
    col2.metric("Militares em férias hoje", em_ferias)

    st.write("---")
    st.subheader("Últimos afastamentos lançados")
    sorted_leaves = sorted(state.leaves, key=lambda x: x.createdAt, reverse=True)[:10]

    rows = []
    for l in sorted_leaves:
        p = find_person_by_id(state, l.personnel_id)
        rows.append({
            "Militar": p.nome if p else "(desconhecido)",
            "Grad": p.grad if p else "",
            "Tipo": l.type,
            "Início": l.startDate,
            "Fim": l.endDate,
            "Descrição": l.description,
        })

    if rows:
        st.table(rows)
    else:
        st.info("Ainda não há afastamentos cadastrados.")


def page_personnel(state: AppState):
    st.header("👮‍♂️ Gestão de Efetivo")

    # Filtro de busca
    search = st.text_input("Buscar por nome ou matrícula")
    filtered = state.personnel
    if search:
        search_lower = search.lower()
        filtered = [
            p for p in state.personnel
            if search_lower in p.nome.lower() or search_lower in p.matr.lower()
        ]

    st.subheader("Lista de militares")
    if filtered:
        st.dataframe(
            [
                {
                    "ID": p.id,
                    "Ant": p.ant,
                    "Grad": p.grad,
                    "Nome": p.nome,
                    "Matr": p.matr,
                    "Unid": p.unid,
                    "Seção": p.secao,
                    "Situação": p.situacao,
                    "Escala": p.esc,
                    "Saldo Férias": p.saldoFerias,
                    "Saldo Abono": p.saldoAbono,
                    "Perfil": p.role,
                }
                for p in filtered
            ],
            use_container_width=True,
        )
    else:
        st.info("Nenhum militar encontrado com esse filtro.")

    st.write("---")
    st.subheader("Cadastrar novo militar")

    with st.form("novo_militar"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome completo")
            matr = st.text_input("Matrícula")
            ant = st.number_input("Antiguidade (número)", min_value=1, step=1, value=1)
            grad = st.selectbox("Graduação", [r.value for r in Rank])
            quadro = st.text_input("Quadro (ex: QOPM, QPPMC, CIVIL)", value="QOPM")
        with col2:
            unid = st.text_input("Unidade", value="DLF")
            secao = st.text_input("Seção", value="SAD")
            situacao = st.text_input("Situação", value="ATIVO")
            esc = st.text_input("Escala", value="EXP")
            saldo_ferias = st.number_input("Saldo de férias (dias)", min_value=0, step=1, value=30)
            saldo_abono = st.number_input("Saldo de abono (dias)", min_value=0, step=1, value=5)
            role = st.selectbox("Perfil de acesso", [r.value for r in UserRole])

        submitted = st.form_submit_button("Salvar militar")

        if submitted:
            if not nome or not matr:
                st.error("Nome e matrícula são obrigatórios.")
            else:
                new = Personnel(
                    id=generate_id("P", state.personnel),
                    ant=int(ant),
                    grad=grad,
                    quadro=quadro,
                    nome=nome,
                    matr=matr,
                    unid=unid,
                    secao=secao,
                    situacao=situacao,
                    esc=esc,
                    saldoFerias=int(saldo_ferias),
                    saldoAbono=int(saldo_abono),
                    role=role,
                )
                state.personnel.append(new)
                save_state(state)
                st.success(f"Militar {nome} cadastrado com sucesso!")
                st.experimental_rerun()


def page_leaves(state: AppState):
    st.header("📅 Lançamento de afastamentos")

    if not state.personnel:
        st.warning("Primeiro cadastre ao menos um militar na aba 'Efetivo'.")
        return

    # Escolher militar
    options = {
        f"{p.nome} ({p.grad} - {p.matr})": p.id for p in state.personnel
    }
    label = st.selectbox("Selecione o militar", list(options.keys()))
    selected_id = options[label]
    person = find_person_by_id(state, selected_id)

    st.subheader(f"Dados do militar selecionado")
    st.write(f"**Nome:** {person.nome}")
    st.write(f"**Graduação:** {person.grad}")
    st.write(f"**Matrícula:** {person.matr}")
    st.write(f"**Unidade/Seção:** {person.unid} / {person.secao}")
    st.write(f"**Situação:** {person.situacao}")
    st.write(f"**Escala:** {person.esc}")
    st.write(f"**Saldo Férias:** {person.saldoFerias} dias")
    st.write(f"**Saldo Abono:** {person.saldoAbono} dias")

    st.write("---")
    st.subheader("Novo afastamento")

    with st.form("novo_afastamento"):
        tipo = st.selectbox(
            "Tipo de afastamento",
            [t.value for t in LeaveType]
        )
        start = st.date_input("Data de início", value=date.today())
        end = st.date_input("Data de término", value=date.today())
        desc = st.text_area("Descrição/Observações", value="")

        enviar = st.form_submit_button("Lançar afastamento")

        if enviar:
            if end < start:
                st.error("Data de término não pode ser anterior à data de início.")
            else:
                new_leave = LeaveRecord(
                    id=generate_id("L", state.leaves),
                    personnel_id=person.id,
                    type=tipo,
                    startDate=start.isoformat(),
                    endDate=end.isoformat(),
                    description=desc,
                    createdAt=datetime.now().isoformat(),
                )
                state.leaves.append(new_leave)

                # Atualização simples de saldos (somente para FÉRIAS/ABONO)
                days = (end - start).days + 1
                if tipo == LeaveType.FERIAS.value:
                    person.saldoFerias = max(0, person.saldoFerias - days)
                if tipo == LeaveType.ABONO.value:
                    person.saldoAbono = max(0, person.saldoAbono - days)

                save_state(state)
                st.success("Afastamento lançado com sucesso!")
                st.experimental_rerun()

    st.write("---")
    st.subheader("Afastamentos já lançados para este militar")

    person_leaves = get_leaves_for_person(state, person.id)
    if person_leaves:
        rows = [
            {
                "Tipo": l.type,
                "Início": l.startDate,
                "Fim": l.endDate,
                "Descrição": l.description,
            }
            for l in sorted(person_leaves, key=lambda x: x.startDate, reverse=True)
        ]
        st.table(rows)
    else:
        st.info("Este militar ainda não possui afastamentos lançados.")


def page_reports(state: AppState):
    st.header("📈 Relatórios simples")

    st.subheader("Total de afastamentos por tipo")
    counts: Dict[str, int] = {}
    for l in state.leaves:
        counts[l.type] = counts.get(l.type, 0) + 1

    if counts:
        rows = [{"Tipo": k, "Quantidade": v} for k, v in counts.items()]
        st.table(rows)
    else:
        st.info("Ainda não há afastamentos lançados.")

    st.write("---")
    st.subheader("Exportar dados brutos (JSON)")
    st.code(DATA_FILE.resolve().as_posix())
    st.write("Você pode abrir esse arquivo com qualquer editor de texto ou usar em outro sistema.")


# ==========================
#  APP PRINCIPAL
# ==========================

def main():
    st.set_page_config(
        page_title="Gestão de Efetivo - DLF/SAD",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Carrega estado na sessão
    if "state" not in st.session_state:
        st.session_state.state = load_state()

    state: AppState = st.session_state.state

    st.sidebar.title("Gestão de Efetivo")
    page = st.sidebar.radio(
        "Navegação",
        ("Dashboard", "Efetivo", "Afastamentos", "Relatórios"),
    )

    if page == "Dashboard":
        page_dashboard(state)
    elif page == "Efetivo":
        page_personnel(state)
    elif page == "Afastamentos":
        page_leaves(state)
    elif page == "Relatórios":
        page_reports(state)


if __name__ == "__main__":
    main()
