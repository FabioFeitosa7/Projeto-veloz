import { useCallback, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import StatusMessage from '../components/StatusMessage.jsx'
import { dashboardApi } from '../services/api.js'

const rotulos = {
  dentro_da_validade: 'Dentro da validade',
  proximo_do_vencimento: 'Próximo do vencimento',
  vence_hoje: 'Vence hoje',
  vencido: 'Vencido',
}

export default function DashboardPage() {
  const location = useLocation()
  const [estado, setEstado] = useState({ carregando: true, dados: null, erro: '' })

  const carregar = useCallback(async (signal) => {
    setEstado((atual) => ({ ...atual, carregando: true, erro: '' }))
    try {
      const dados = await dashboardApi.obter({ signal })
      setEstado({ carregando: false, dados, erro: '' })
    } catch (erro) {
      if (erro.name !== 'AbortError') {
        setEstado({ carregando: false, dados: null, erro: erro.message })
      }
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    dashboardApi.obter({ signal: controller.signal })
      .then((dados) => setEstado({ carregando: false, dados, erro: '' }))
      .catch((erro) => {
        if (erro.name !== 'AbortError') {
          setEstado({ carregando: false, dados: null, erro: erro.message })
        }
      })
    return () => controller.abort()
  }, [])

  if (estado.carregando) return <StatusMessage>Carregando o estoque…</StatusMessage>
  if (estado.erro) return <StatusMessage tipo="erro" onRetry={() => carregar()}>{estado.erro}</StatusMessage>

  const { totais, ingredientes } = estado.dados
  return (
    <section>
      <div className="page-heading">
        <div><span className="eyebrow">Visão geral</span><h1>Painel do estoque</h1></div>
        <span className="date-chip">Atualizado em {new Date(`${estado.dados.data}T12:00:00`).toLocaleDateString('pt-BR')}</span>
      </div>
      {location.state?.mensagem && <StatusMessage tipo="sucesso">{location.state.mensagem}</StatusMessage>}
      <div className="metrics" aria-label="Resumo do estoque">
        <article><span>Ingredientes ativos</span><strong>{totais.ingredientes}</strong></article>
        <article><span>Próximos do vencimento</span><strong>{totais.proximos_do_vencimento}</strong></article>
        <article className="danger"><span>Vencidos</span><strong>{totais.vencidos}</strong></article>
      </div>
      <div className="panel">
        <div className="panel-heading"><div><h2>Ingredientes</h2><p>Quantidade atual e situação da validade.</p></div></div>
        {ingredientes.length === 0 ? (
          <StatusMessage>Nenhum ingrediente ativo foi cadastrado.</StatusMessage>
        ) : (
          <div className="table-wrap"><table className="responsive-table">
            <thead><tr><th>Ingrediente</th><th>Estoque</th><th>Meta</th><th>Validade</th></tr></thead>
            <tbody>{ingredientes.map((item) => (
              <tr key={item.id}>
                <td className="mobile-primary" data-label="Ingrediente"><strong>{item.nome}</strong></td>
                <td data-label="Estoque">{Number(item.estoque_atual).toLocaleString('pt-BR')} {item.unidade_exibicao}</td>
                <td data-label="Meta">{Number(item.meta_atual).toLocaleString('pt-BR')} {item.unidade_exibicao}</td>
                <td data-label="Validade"><span className={`badge badge-${item.validade.situacao}`}>{rotulos[item.validade.situacao]}</span><small>{item.validade.descricao}</small></td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </div>
    </section>
  )
}
