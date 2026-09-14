import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import StatusMessage from '../components/StatusMessage.jsx'
import { fechamentosApi } from '../services/api.js'

function mesAtual() {
  const hoje = new Date()
  return `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, '0')}`
}

export default function FechamentoNewPage() {
  const navigate = useNavigate()
  const [referencia, setReferencia] = useState(mesAtual())
  const [rascunho, setRascunho] = useState(null)
  const [estado, setEstado] = useState({ carregando: true, salvando: false, erro: '' })

  useEffect(() => {
    const controller = new AbortController()
    fechamentosApi.listar({ signal: controller.signal })
      .then((dados) => {
        setRascunho(dados.find((item) => item.status === 'RASCUNHO') || null)
        setEstado((atual) => ({ ...atual, carregando: false }))
      })
      .catch((erro) => {
        if (erro.name !== 'AbortError') setEstado({ carregando: false, salvando: false, erro: erro.message })
      })
    return () => controller.abort()
  }, [])

  async function criar(evento) {
    evento.preventDefault()
    setEstado((atual) => ({ ...atual, salvando: true, erro: '' }))
    try {
      const fechamento = await fechamentosApi.criar(referencia)
      navigate(`/fechamentos/${fechamento.id}/editar`, { replace: true, state: { mensagem: 'Fechamento criado. Preencha os valores mensais.' } })
    } catch (erro) {
      const mensagem = erro.data?.referencia?.join?.(' ') || erro.message
      setEstado((atual) => ({ ...atual, salvando: false, erro: mensagem }))
    }
  }

  if (estado.carregando) return <StatusMessage>Verificando fechamentos…</StatusMessage>

  return (
    <section>
      <div className="page-heading"><div><span className="eyebrow">Fechamento mensal</span><h1>Novo fechamento</h1></div></div>
      {estado.erro && <StatusMessage tipo="erro">{estado.erro}</StatusMessage>}
      {rascunho ? (
        <div className="panel callout-panel">
          <span className="eyebrow">Rascunho encontrado</span>
          <h2>Já existe um fechamento em andamento</h2>
          <p>Continue preenchendo o mês de {new Date(`${rascunho.referencia}T12:00:00`).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })}.</p>
          <Link className="button button-primary" to={`/fechamentos/${rascunho.id}/editar`}>Continuar fechamento</Link>
        </div>
      ) : (
        <form className="panel form-panel compact-form" onSubmit={criar}>
          <h2>Escolha o mês de referência</h2>
          <p>O sistema copiará os ingredientes ativos e suas metas atuais para um novo rascunho.</p>
          <div className="form-grid">
            <label className="field" htmlFor="referencia"><span>Mês de referência</span><input id="referencia" type="month" value={referencia} onChange={(evento) => setReferencia(evento.target.value)} required /></label>
          </div>
          <div className="form-actions"><Link className="button button-secondary" to="/">Cancelar</Link><button className="button button-primary" disabled={estado.salvando}>{estado.salvando ? 'Criando…' : 'Iniciar fechamento'}</button></div>
        </form>
      )}
    </section>
  )
}
