const API_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api').replace(/\/$/, '')

export function apiUrl(caminho) {
  return `${API_URL}${caminho}`
}

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

export async function apiFetch(caminho, opcoes = {}) {
  const resposta = await fetch(`${API_URL}${caminho}`, {
    ...opcoes,
    headers: {
      Accept: 'application/json',
      ...(opcoes.body ? { 'Content-Type': 'application/json' } : {}),
      ...opcoes.headers,
    },
  })
  const contentType = resposta.headers.get('content-type') || ''
  const dados = contentType.includes('application/json') ? await resposta.json() : await resposta.text()
  if (!resposta.ok) {
    const mensagem = dados?.detail || 'Não foi possível concluir a solicitação.'
    throw new ApiError(mensagem, resposta.status, dados)
  }
  return dados
}

export const dashboardApi = {
  obter: ({ signal } = {}) => apiFetch('/dashboard/', { signal }),
}

export const ingredientesApi = {
  listar: ({ busca = '', situacao = 'ativos', signal } = {}) => {
    const parametros = new URLSearchParams({ situacao })
    if (busca) parametros.set('q', busca)
    return apiFetch(`/ingredientes/?${parametros}`, { signal })
  },
  obter: (id, { signal } = {}) => apiFetch(`/ingredientes/${id}/`, { signal }),
  criar: (dados) => apiFetch('/ingredientes/', {
    method: 'POST',
    body: JSON.stringify(dados),
  }),
  atualizar: (id, dados) => apiFetch(`/ingredientes/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(dados),
  }),
  desativar: (id) => apiFetch(`/ingredientes/${id}/desativar/`, { method: 'POST' }),
  reativar: (id) => apiFetch(`/ingredientes/${id}/reativar/`, { method: 'POST' }),
}

export const fechamentosApi = {
  listar: ({ signal } = {}) => apiFetch('/fechamentos/', { signal }),
  obter: (id, { signal } = {}) => apiFetch(`/fechamentos/${id}/`, { signal }),
  criar: (referencia) => apiFetch('/fechamentos/', {
    method: 'POST',
    body: JSON.stringify({ referencia: `${referencia}-01` }),
  }),
  salvarItens: (id, itens) => apiFetch(`/fechamentos/${id}/itens/`, {
    method: 'PATCH',
    body: JSON.stringify({ itens }),
  }),
  revisar: (id, { signal } = {}) => apiFetch(`/fechamentos/${id}/revisao/`, { signal }),
  finalizar: (id) => apiFetch(`/fechamentos/${id}/finalizar/`, { method: 'POST' }),
  cancelar: (id) => apiFetch(`/fechamentos/${id}/cancelar/`, { method: 'POST' }),
}
