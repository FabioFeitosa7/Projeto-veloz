import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App.jsx'

const fechamento = {
  id: 12,
  referencia: '2026-09-01',
  status: 'FINALIZADO',
  total_itens: 1,
  total_compras: 1,
  finalizado_em: '2026-09-30T12:00:00Z',
  cancelado_em: null,
  itens: [{
    id: 31,
    nome_registrado: 'Farinha',
    unidade_exibicao: 'Kg',
    consumo_mensal: '20.000',
    estoque_restante: '6.000',
    houve_falta: false,
    meta_resultante: '20.000',
    quantidade_compra: '14.000',
    linha_compra: 'Comprar: 14 Kg de Farinha',
  }],
}

function respostaJson(dados) {
  return Promise.resolve(new Response(JSON.stringify(dados), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  }))
}

afterEach(() => vi.restoreAllMocks())

describe('Histórico mensal', () => {
  it('lista fechamentos e seus totais', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => respostaJson([fechamento]))

    render(<MemoryRouter initialEntries={['/historico']}><App /></MemoryRouter>)

    await waitFor(() => expect(screen.getByText('setembro de 2026')).toBeInTheDocument())
    expect(screen.getByText('Finalizado')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver detalhes' })).toHaveAttribute('href', '/historico/12')
  })

  it('exibe valores preservados, lista e downloads', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => respostaJson(fechamento))

    render(<MemoryRouter initialEntries={['/historico/12']}><App /></MemoryRouter>)

    await waitFor(() => expect(screen.getByText('Comprar: 14 Kg de Farinha')).toBeInTheDocument())
    expect(screen.getAllByText('20 Kg')).toHaveLength(2)
    expect(screen.getByRole('link', { name: 'TXT' })).toHaveAttribute('href', 'http://127.0.0.1:8000/api/fechamentos/12/lista.txt')
    expect(screen.getByRole('link', { name: 'CSV' })).toHaveAttribute('href', 'http://127.0.0.1:8000/api/fechamentos/12/lista.csv')
  })

  it('permite continuar um rascunho sem oferecer downloads', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => respostaJson({ ...fechamento, status: 'RASCUNHO', total_compras: 0 }))
    render(<MemoryRouter initialEntries={['/historico/12']}><App /></MemoryRouter>)

    const continuar = await screen.findByRole('link', { name: 'Continuar rascunho' })
    expect(continuar).toHaveAttribute('href', '/fechamentos/12/editar')
    expect(screen.queryByRole('link', { name: 'TXT' })).not.toBeInTheDocument()
    expect(screen.queryByText('Lista de compras')).not.toBeInTheDocument()
  })

  it('mostra estado vazio do histórico', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => respostaJson([]))
    render(<MemoryRouter initialEntries={['/historico']}><App /></MemoryRouter>)

    expect(await screen.findByText('Nenhum fechamento foi criado ainda.')).toBeInTheDocument()
  })

  it('exibe cancelado sem permitir edicao ou downloads', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => respostaJson({
      ...fechamento,
      status: 'CANCELADO',
      cancelado_em: '2026-09-29T12:00:00Z',
      total_compras: 0,
    }))
    render(<MemoryRouter initialEntries={['/historico/12']}><App /></MemoryRouter>)

    expect(await screen.findByText('Cancelado')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Continuar rascunho' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'TXT' })).not.toBeInTheDocument()
  })
})
