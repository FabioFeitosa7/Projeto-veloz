import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import StatusMessage from '../components/StatusMessage.jsx'
import { fechamentosApi } from '../services/api.js'

function prepararItens(itens) {
  return itens.map((item) => ({
    ...item,
    consumo_mensal: item.consumo_mensal ?? '',
    estoque_restante: item.estoque_restante ?? '',
    validade_registrada: item.validade_registrada ?? '',
  }))
}

function mensagemDeErro(erro) {
  if (erro.data?.itens && typeof erro.data.itens === 'object') {
    return Object.values(erro.data.itens)
      .flatMap((campos) => Object.values(campos))
      .flat()
      .join(' ')
  }
  return erro.message
}

function itensParaSalvar(itens) {
  return itens.map((item) => ({
    id: item.id,
    consumo_mensal: item.consumo_mensal === '' ? null : item.consumo_mensal,
    estoque_restante: item.estoque_restante === '' ? null : item.estoque_restante,
    validade_registrada: item.validade_registrada || null,
    houve_falta: item.houve_falta,
  }))
}

export default function FechamentoEditPage() {
  const { id } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const [validacaoAtiva, setValidacaoAtiva] = useState(false)
  const [estado, setEstado] = useState({ carregando: true, salvando: false, fechamento: null, erro: '', sucesso: location.state?.mensagem || '' })

  useEffect(() => {
    const controller = new AbortController()
    fechamentosApi.obter(id, { signal: controller.signal })
      .then((fechamento) => setEstado((atual) => ({ ...atual, carregando: false, fechamento: { ...fechamento, itens: prepararItens(fechamento.itens) } })))
      .catch((erro) => { if (erro.name !== 'AbortError') setEstado((atual) => ({ ...atual, carregando: false, erro: erro.message })) })
    return () => controller.abort()
  }, [id])

  const preenchidos = useMemo(() => estado.fechamento?.itens.filter((item) => (
    item.consumo_mensal !== '' && item.estoque_restante !== '' && item.validade_registrada !== ''
  )).length || 0, [estado.fechamento])

  function alterarItem(itemId, campo, valor) {
    setEstado((atual) => ({
      ...atual,
      erro: '',
      sucesso: '',
      fechamento: {
        ...atual.fechamento,
        itens: atual.fechamento.itens.map((item) => item.id === itemId ? { ...item, [campo]: valor } : item),
      },
    }))
  }

  async function salvar(evento) {
    evento.preventDefault()
    const revisar = evento.nativeEvent.submitter?.value === 'revisar'
    if (revisar && preenchidos !== estado.fechamento.itens.length) {
      setValidacaoAtiva(true)
      setEstado((atual) => ({ ...atual, erro: 'Preencha consumo, estoque e validade de todos os ingredientes antes de revisar.', sucesso: '' }))
      requestAnimationFrame(() => {
        document.querySelector('[aria-invalid="true"]')?.focus({ preventScroll: true })
        window.scrollTo({ top: 0, left: 0, behavior: 'smooth' })
      })
      return
    }
    setValidacaoAtiva(false)
    setEstado((atual) => ({ ...atual, salvando: true, erro: '', sucesso: '' }))
    const itens = itensParaSalvar(estado.fechamento.itens)
    try {
      const fechamento = await fechamentosApi.salvarItens(id, itens)
      if (revisar) {
        navigate(`/fechamentos/${id}/revisao`)
        return
      }
      setEstado({ carregando: false, salvando: false, fechamento: { ...fechamento, itens: prepararItens(fechamento.itens) }, erro: '', sucesso: 'Rascunho salvo. Nenhuma meta foi alterada.' })
    } catch (erro) {
      setEstado((atual) => ({ ...atual, salvando: false, erro: mensagemDeErro(erro) }))
    }
  }

  async function sairSalvando() {
    setEstado((atual) => ({ ...atual, salvando: true, erro: '', sucesso: '' }))
    try {
      await fechamentosApi.salvarItens(id, itensParaSalvar(estado.fechamento.itens))
      navigate('/', { state: { mensagem: 'Rascunho salvo automaticamente.' } })
    } catch (erro) {
      setEstado((atual) => ({ ...atual, salvando: false, erro: mensagemDeErro(erro) }))
      window.scrollTo({ top: 0, left: 0, behavior: 'smooth' })
    }
  }

  async function cancelar() {
    if (!window.confirm('Cancelar este fechamento? Os dados ficarão no histórico, mas o rascunho não poderá mais ser editado.')) return
    setEstado((atual) => ({ ...atual, salvando: true, erro: '', sucesso: '' }))
    try {
      await fechamentosApi.cancelar(id)
      navigate(`/historico/${id}`, { replace: true, state: { mensagem: 'Fechamento cancelado e mantido no histórico.' } })
    } catch (erro) {
      setEstado((atual) => ({ ...atual, salvando: false, erro: erro.message }))
    }
  }

  if (estado.carregando) return <StatusMessage>Carregando fechamento…</StatusMessage>
  if (!estado.fechamento) return <StatusMessage tipo="erro" onRetry={() => navigate('/fechamentos/novo')}>{estado.erro || 'Fechamento não encontrado.'}</StatusMessage>
  if (estado.fechamento.status !== 'RASCUNHO') return <StatusMessage tipo="erro">Este fechamento não está mais em rascunho e não pode ser editado.</StatusMessage>

  const referencia = new Date(`${estado.fechamento.referencia}T12:00:00`).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
  return (
    <section>
      <div className="page-heading"><div><span className="eyebrow">Fechamento mensal</span><h1>{referencia}</h1></div><span className="date-chip">{preenchidos} de {estado.fechamento.itens.length} preenchidos</span></div>
      {estado.sucesso && <StatusMessage tipo="sucesso">{estado.sucesso}</StatusMessage>}
      {estado.erro && <StatusMessage tipo="erro">{estado.erro}</StatusMessage>}
      <form className="panel closing-form" onSubmit={salvar} noValidate>
        <div className="panel-heading"><div><h2>Consumo do mês</h2><p>Você pode preencher aos poucos. Ao sair, o sistema salva tudo como rascunho.</p></div></div>
        <div className="closing-items">{estado.fechamento.itens.map((item) => (
          <fieldset className="closing-item" key={item.id}>
            <legend><strong>{item.nome_registrado}</strong><span>Meta atual: {Number(item.meta_anterior).toLocaleString('pt-BR')} {item.unidade_exibicao}</span></legend>
            <div className="closing-item-fields">
              <label className="field"><span>Consumo mensal</span><input aria-label={`Consumo mensal de ${item.nome_registrado}`} aria-invalid={validacaoAtiva && item.consumo_mensal === ''} aria-describedby={validacaoAtiva && item.consumo_mensal === '' ? `erro-consumo-${item.id}` : undefined} type="number" min="0" step={item.unidade_registrada === 'UN' ? '1' : '0.001'} value={item.consumo_mensal} onChange={(evento) => alterarItem(item.id, 'consumo_mensal', evento.target.value)} />{validacaoAtiva && item.consumo_mensal === '' && <span className="field-error" id={`erro-consumo-${item.id}`}>Campo obrigatório</span>}</label>
              <label className="field"><span>Estoque restante</span><input aria-label={`Estoque restante de ${item.nome_registrado}`} aria-invalid={validacaoAtiva && item.estoque_restante === ''} aria-describedby={validacaoAtiva && item.estoque_restante === '' ? `erro-estoque-${item.id}` : undefined} type="number" min="0" step={item.unidade_registrada === 'UN' ? '1' : '0.001'} value={item.estoque_restante} onChange={(evento) => alterarItem(item.id, 'estoque_restante', evento.target.value)} />{validacaoAtiva && item.estoque_restante === '' && <span className="field-error" id={`erro-estoque-${item.id}`}>Campo obrigatório</span>}</label>
              <label className="field"><span>Validade considerada</span><input aria-label={`Validade de ${item.nome_registrado}`} aria-invalid={validacaoAtiva && item.validade_registrada === ''} aria-describedby={validacaoAtiva && item.validade_registrada === '' ? `erro-validade-${item.id}` : undefined} type="date" value={item.validade_registrada} onChange={(evento) => alterarItem(item.id, 'validade_registrada', evento.target.value)} />{validacaoAtiva && item.validade_registrada === '' && <span className="field-error" id={`erro-validade-${item.id}`}>Campo obrigatório</span>}</label>
              <label className="checkbox-field"><input aria-label={`Houve falta de ${item.nome_registrado}`} type="checkbox" checked={item.houve_falta} onChange={(evento) => { alterarItem(item.id, 'houve_falta', evento.target.checked); if (evento.target.checked) alterarItem(item.id, 'estoque_restante', '0') }} /><span>Acabou antes do fim do mês</span></label>
            </div>
          </fieldset>
        ))}</div>
        <div className="form-actions sticky-actions"><button type="button" className="button button-danger button-left" onClick={cancelar} disabled={estado.salvando}>Cancelar fechamento</button><button type="button" className="button button-secondary" onClick={sairSalvando} disabled={estado.salvando}>Sair e salvar</button><button className="button button-secondary" value="salvar" disabled={estado.salvando}>{estado.salvando ? 'Salvando…' : 'Salvar rascunho'}</button><button className="button button-primary" value="revisar" disabled={estado.salvando}>Salvar e revisar</button></div>
      </form>
    </section>
  )
}
