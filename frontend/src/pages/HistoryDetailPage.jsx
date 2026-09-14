import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import StatusMessage from '../components/StatusMessage.jsx'
import { apiUrl, fechamentosApi } from '../services/api.js'

function numero(valor) {
  if (valor === null || valor === undefined) return '—'
  return Number(valor).toLocaleString('pt-BR', { maximumFractionDigits: 3 })
}

export default function HistoryDetailPage() {
  const { id } = useParams()
  const location = useLocation()
  const [estado, setEstado] = useState({ carregando: true, fechamento: null, erro: '' })

  useEffect(() => {
    const controller = new AbortController()
    fechamentosApi.obter(id, { signal: controller.signal })
      .then((fechamento) => setEstado({ carregando: false, fechamento, erro: '' }))
      .catch((erro) => { if (erro.name !== 'AbortError') setEstado({ carregando: false, fechamento: null, erro: erro.message }) })
    return () => controller.abort()
  }, [id])

  if (estado.carregando) return <StatusMessage>Carregando fechamento…</StatusMessage>
  if (!estado.fechamento) return <StatusMessage tipo="erro">{estado.erro || 'Fechamento não encontrado.'}</StatusMessage>
  const fechamento = estado.fechamento
  const finalizado = fechamento.status === 'FINALIZADO'
  const rascunho = fechamento.status === 'RASCUNHO'
  const compras = fechamento.itens.filter((item) => item.linha_compra)
  const referencia = new Date(`${fechamento.referencia}T12:00:00`).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })

  return (
    <section>
      <div className="page-heading"><div><span className="eyebrow">Histórico mensal</span><h1 className="capitalize">{referencia}</h1></div><div className="heading-actions"><Link className="button button-secondary" to="/historico">Voltar</Link>{rascunho && <Link className="button button-primary" to={`/fechamentos/${id}/editar`}>Continuar rascunho</Link>}</div></div>
      {location.state?.mensagem && <StatusMessage tipo="sucesso">{location.state.mensagem}</StatusMessage>}
      <div className="panel history-summary"><div><span>Situação</span><strong>{finalizado ? 'Finalizado' : rascunho ? 'Rascunho' : 'Cancelado'}</strong></div><div><span>Ingredientes</span><strong>{fechamento.itens.length}</strong></div><div><span>Itens para comprar</span><strong>{finalizado ? compras.length : '—'}</strong></div></div>
      <div className="panel history-items"><div className="panel-heading"><div><h2>Itens registrados</h2><p>Valores preservados para este mês.</p></div></div><div className="table-wrap"><table className="responsive-table">
        <thead><tr><th>Ingrediente</th><th>Consumo</th><th>Estoque restante</th><th>Meta resultante</th><th>Compra</th></tr></thead>
        <tbody>{fechamento.itens.map((item) => <tr key={item.id}><td className="mobile-primary" data-label="Ingrediente"><strong>{item.nome_registrado}</strong><small>{item.houve_falta ? 'Houve falta antecipada' : 'Sem falta antecipada'}</small></td><td data-label="Consumo">{numero(item.consumo_mensal)} {item.unidade_exibicao}</td><td data-label="Estoque restante">{numero(item.estoque_restante)} {item.unidade_exibicao}</td><td data-label="Meta resultante">{numero(item.meta_resultante)} {item.unidade_exibicao}</td><td data-label="Compra">{numero(item.quantidade_compra)} {item.unidade_exibicao}</td></tr>)}</tbody>
      </table></div></div>
      {finalizado && <div className="panel shopping-preview"><div className="panel-heading"><div><h2>Lista de compras</h2><p>Itens com quantidade positiva.</p></div><div className="heading-actions"><a className="button button-secondary" href={apiUrl(`/fechamentos/${id}/lista.txt`)}>TXT</a><a className="button button-secondary" href={apiUrl(`/fechamentos/${id}/lista.csv`)}>CSV</a></div></div><div className="shopping-lines">{compras.length ? compras.map((item) => <p key={item.id}>{item.linha_compra}</p>) : <p>Nenhum item precisa ser comprado.</p>}</div></div>}
    </section>
  )
}
