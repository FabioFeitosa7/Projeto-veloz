import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import IngredientStatus from '../components/IngredientStatus.jsx'
import StatusMessage from '../components/StatusMessage.jsx'
import { ingredientesApi } from '../services/api.js'

export default function IngredientesPage() {
  const location = useLocation()
  const [busca, setBusca] = useState('')
  const [situacao, setSituacao] = useState('ativos')
  const [recarregar, setRecarregar] = useState(0)
  const [estado, setEstado] = useState({ carregando: true, dados: [], erro: '' })

  useEffect(() => {
    const controller = new AbortController()
    const atraso = setTimeout(() => {
      setEstado((atual) => ({ ...atual, carregando: true, erro: '' }))
      ingredientesApi.listar({ busca, situacao, signal: controller.signal })
        .then((dados) => setEstado({ carregando: false, dados, erro: '' }))
        .catch((erro) => {
          if (erro.name !== 'AbortError') setEstado({ carregando: false, dados: [], erro: erro.message })
        })
    }, 250)
    return () => { clearTimeout(atraso); controller.abort() }
  }, [busca, situacao, recarregar])

  return (
    <section>
      <div className="page-heading">
        <div><span className="eyebrow">Cadastro</span><h1>Ingredientes</h1></div>
        <Link className="button button-primary" to="/ingredientes/novo">Novo ingrediente</Link>
      </div>
      {location.state?.mensagem && <StatusMessage tipo="sucesso">{location.state.mensagem}</StatusMessage>}
      <div className="panel">
        <div className="filters">
          <label><span>Buscar</span><input value={busca} onChange={(evento) => setBusca(evento.target.value)} placeholder="Nome do ingrediente" /></label>
          <label><span>Situação</span><select value={situacao} onChange={(evento) => setSituacao(evento.target.value)}><option value="ativos">Ativos</option><option value="inativos">Inativos</option><option value="todos">Todos</option></select></label>
        </div>
        {estado.carregando ? <StatusMessage>Carregando ingredientes…</StatusMessage> : estado.erro ? (
          <StatusMessage tipo="erro" onRetry={() => setRecarregar((valor) => valor + 1)}>{estado.erro}</StatusMessage>
        ) : estado.dados.length === 0 ? (
          <StatusMessage>Nenhum ingrediente encontrado para estes filtros.</StatusMessage>
        ) : (
          <div className="table-wrap"><table className="responsive-table">
            <thead><tr><th>Ingrediente</th><th>Estoque atual</th><th>Meta mensal</th><th>Validade</th><th><span className="sr-only">Ações</span></th></tr></thead>
            <tbody>{estado.dados.map((item) => <tr key={item.id}>
              <td className="mobile-primary" data-label="Ingrediente"><Link className="table-link" to={`/ingredientes/${item.id}`}>{item.nome}</Link>{!item.ativo && <small>Inativo</small>}</td>
              <td data-label="Estoque atual">{Number(item.estoque_atual).toLocaleString('pt-BR')} {item.unidade_exibicao}</td>
              <td data-label="Meta mensal">{Number(item.meta_atual).toLocaleString('pt-BR')} {item.unidade_exibicao}</td>
              <td data-label="Validade"><IngredientStatus validade={item.validade} /><small>{item.validade.descricao}</small></td>
              <td className="mobile-action" data-label="Ações"><Link className="text-link" to={`/ingredientes/${item.id}`}>Ver detalhes</Link></td>
            </tr>)}</tbody>
          </table></div>
        )}
      </div>
    </section>
  )
}
