import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import StatusMessage from '../components/StatusMessage.jsx'
import { apiUrl, fechamentosApi } from '../services/api.js'

const motivos = {
  normal: 'Reposição normal',
  falta: 'Falta antecipada',
  vencimento: 'Produto vencido',
  falta_e_vencimento: 'Falta e vencimento',
}

function numero(valor) {
  return Number(valor).toLocaleString('pt-BR', { maximumFractionDigits: 3 })
}

export default function FechamentoReviewPage() {
  const { id } = useParams()
  const [estado, setEstado] = useState({ carregando: true, revisao: null, erro: '', finalizando: false, finalizado: false })

  useEffect(() => {
    const controller = new AbortController()
    fechamentosApi.revisar(id, { signal: controller.signal })
      .then((revisao) => setEstado((atual) => ({ ...atual, carregando: false, revisao })))
      .catch((erro) => { if (erro.name !== 'AbortError') setEstado((atual) => ({ ...atual, carregando: false, erro: erro.message })) })
    return () => controller.abort()
  }, [id])

  async function finalizar() {
    if (!window.confirm('Finalizar este fechamento? Depois disso, os dados e as metas serão atualizados e o mês não poderá mais ser editado.')) return
    setEstado((atual) => ({ ...atual, finalizando: true, erro: '' }))
    try {
      await fechamentosApi.finalizar(id)
      setEstado((atual) => ({ ...atual, finalizando: false, finalizado: true }))
    } catch (erro) {
      setEstado((atual) => ({ ...atual, finalizando: false, erro: erro.message }))
    }
  }

  if (estado.carregando) return <StatusMessage>Calculando a revisão…</StatusMessage>
  if (!estado.revisao) return <section><StatusMessage tipo="erro">{estado.erro || 'Não foi possível revisar o fechamento.'}</StatusMessage><Link className="button button-secondary" to={`/fechamentos/${id}/editar`}>Voltar ao preenchimento</Link></section>

  const compras = estado.revisao.itens.filter((item) => item.linha_compra)
  if (estado.finalizado) return (
    <section>
      <div className="page-heading"><div><span className="eyebrow">Fechamento mensal</span><h1>Fechamento finalizado</h1></div></div>
      <StatusMessage tipo="sucesso">As metas e o estoque foram atualizados com sucesso.</StatusMessage>
      <div className="panel completion-panel"><h2>Lista pronta para levar ao mercado</h2><p>Baixe a lista no formato que preferir ou volte ao painel.</p><div className="heading-actions"><a className="button button-secondary" href={apiUrl(`/fechamentos/${id}/lista.txt`)}>Baixar TXT</a><a className="button button-secondary" href={apiUrl(`/fechamentos/${id}/lista.csv`)}>Baixar CSV</a><Link className="button button-primary" to="/">Voltar ao painel</Link></div></div>
    </section>
  )

  return (
    <section>
      <div className="page-heading"><div><span className="eyebrow">Confira antes de confirmar</span><h1>Revisão do fechamento</h1></div><span className="date-chip">{compras.length} itens para comprar</span></div>
      {estado.erro && <StatusMessage tipo="erro">{estado.erro}</StatusMessage>}
      <div className="review-grid">{estado.revisao.itens.map((item) => (
        <article className="panel review-card" key={item.id}>
          <div className="review-card-heading"><div><h2>{item.ingrediente}</h2><span className={`badge reason-${item.motivo}`}>{motivos[item.motivo]}</span></div><strong>{item.linha_compra ? `${numero(item.quantidade_compra)} ${item.unidade_exibicao}` : 'Nada a comprar'}</strong></div>
          <dl><div><dt>Meta anterior</dt><dd>{numero(item.meta_anterior)} {item.unidade_exibicao}</dd></div><div><dt>Nova meta</dt><dd>{numero(item.meta_resultante)} {item.unidade_exibicao}</dd></div><div><dt>Estoque aproveitável</dt><dd>{numero(item.estoque_aproveitavel)} {item.unidade_exibicao}</dd></div></dl>
          <p>{item.explicacao}</p>
        </article>
      ))}</div>
      <div className="panel shopping-preview"><div className="panel-heading"><div><h2>Prévia da lista de compras</h2><p>Apenas quantidades maiores que zero aparecem.</p></div></div><div className="shopping-lines">{compras.length ? compras.map((item) => <p key={item.id}>{item.linha_compra}</p>) : <p>Nenhum item precisa ser comprado.</p>}</div></div>
      <div className="form-actions review-actions"><Link className="button button-secondary" to={`/fechamentos/${id}/editar`}>Voltar e corrigir</Link><button className="button button-primary" onClick={finalizar} disabled={estado.finalizando}>{estado.finalizando ? 'Finalizando…' : 'Finalizar fechamento'}</button></div>
    </section>
  )
}
