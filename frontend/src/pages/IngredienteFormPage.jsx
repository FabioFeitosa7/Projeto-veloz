import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import StatusMessage from '../components/StatusMessage.jsx'
import { ingredientesApi } from '../services/api.js'

const formularioInicial = { nome: '', unidade: 'KG', meta_atual: '', estoque_atual: '', data_validade: '' }

function mensagensErro(dados) {
  if (!dados || typeof dados !== 'object') return {}
  return Object.fromEntries(Object.entries(dados).map(([campo, mensagens]) => [
    campo,
    Array.isArray(mensagens) ? mensagens.join(' ') : String(mensagens),
  ]))
}

export default function IngredienteFormPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const editando = Boolean(id)
  const [formulario, setFormulario] = useState(formularioInicial)
  const [estado, setEstado] = useState({ carregando: editando, salvando: false, erro: '', campos: {} })

  useEffect(() => {
    if (!editando) return undefined
    const controller = new AbortController()
    ingredientesApi.obter(id, { signal: controller.signal })
      .then((item) => {
        setFormulario({ nome: item.nome, unidade: item.unidade, meta_atual: item.meta_atual, estoque_atual: item.estoque_atual, data_validade: item.data_validade })
        setEstado((atual) => ({ ...atual, carregando: false }))
      })
      .catch((erro) => {
        if (erro.name !== 'AbortError') setEstado((atual) => ({ ...atual, carregando: false, erro: erro.message }))
      })
    return () => controller.abort()
  }, [editando, id])

  function alterar(evento) {
    const { name, value } = evento.target
    setFormulario((atual) => ({ ...atual, [name]: value }))
    setEstado((atual) => ({ ...atual, campos: { ...atual.campos, [name]: '' } }))
  }

  async function salvar(evento) {
    evento.preventDefault()
    setEstado((atual) => ({ ...atual, salvando: true, erro: '', campos: {} }))
    try {
      const item = editando
        ? await ingredientesApi.atualizar(id, formulario)
        : await ingredientesApi.criar(formulario)
      navigate(`/ingredientes/${item.id}`, { replace: true, state: { mensagem: `Ingrediente ${editando ? 'atualizado' : 'cadastrado'} com sucesso.` } })
    } catch (erro) {
      setEstado((atual) => ({ ...atual, salvando: false, erro: erro.data?.detail ? erro.message : '', campos: mensagensErro(erro.data) }))
    }
  }

  if (estado.carregando) return <StatusMessage>Carregando ingrediente…</StatusMessage>
  if (estado.erro && editando && !formulario.nome) return <StatusMessage tipo="erro">{estado.erro}</StatusMessage>

  return (
    <section>
      <div className="page-heading"><div><span className="eyebrow">Ingredientes</span><h1>{editando ? 'Editar ingrediente' : 'Novo ingrediente'}</h1></div></div>
      <form className="panel form-panel" onSubmit={salvar} noValidate>
        {estado.erro && <StatusMessage tipo="erro">{estado.erro}</StatusMessage>}
        {estado.campos.non_field_errors && <StatusMessage tipo="erro">{estado.campos.non_field_errors}</StatusMessage>}
        <div className="form-grid">
          <Campo label="Nome do ingrediente" nome="nome" erro={estado.campos.nome}><input id="nome" name="nome" value={formulario.nome} onChange={alterar} required autoFocus /></Campo>
          <Campo label="Unidade de medida" nome="unidade" erro={estado.campos.unidade}><select id="unidade" name="unidade" value={formulario.unidade} onChange={alterar}><option value="KG">Kg</option><option value="L">Litros</option><option value="UN">Unidades</option></select></Campo>
          <Campo label="Meta mensal" nome="meta_atual" erro={estado.campos.meta_atual}><input id="meta_atual" name="meta_atual" type="number" min="0.001" step={formulario.unidade === 'UN' ? '1' : '0.001'} value={formulario.meta_atual} onChange={alterar} required /></Campo>
          <Campo label="Estoque atual" nome="estoque_atual" erro={estado.campos.estoque_atual}><input id="estoque_atual" name="estoque_atual" type="number" min="0" step={formulario.unidade === 'UN' ? '1' : '0.001'} value={formulario.estoque_atual} onChange={alterar} required /></Campo>
          <Campo label="Data de validade" nome="data_validade" erro={estado.campos.data_validade}><input id="data_validade" name="data_validade" type="date" value={formulario.data_validade} onChange={alterar} required /></Campo>
        </div>
        <div className="form-actions"><Link className="button button-secondary" to={editando ? `/ingredientes/${id}` : '/ingredientes'}>Cancelar</Link><button className="button button-primary" disabled={estado.salvando}>{estado.salvando ? 'Salvando…' : 'Salvar ingrediente'}</button></div>
      </form>
    </section>
  )
}

function Campo({ label, nome, erro, children }) {
  return <label className="field" htmlFor={nome}><span>{label}</span>{children}{erro && <small className="field-error">{erro}</small>}</label>
}
