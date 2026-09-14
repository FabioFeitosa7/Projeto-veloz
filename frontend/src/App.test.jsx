import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App.jsx'

afterEach(() => vi.restoreAllMocks())

describe('App', () => {
  it('abre e fecha a navegação compacta', () => {
    render(<MemoryRouter initialEntries={['/rota-inexistente']}><App /></MemoryRouter>)

    const menu = screen.getByRole('button', { name: 'Menu' })
    expect(menu).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(menu)
    expect(screen.getByRole('button', { name: 'Fechar' })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('navigation', { name: 'Navegação principal' })).toHaveClass('nav-open')
    fireEvent.click(screen.getByRole('button', { name: 'Fechar' }))
    expect(screen.getByRole('button', { name: 'Menu' })).toHaveAttribute('aria-expanded', 'false')
  })

  it('carrega o painel usando a API Django', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      data: '2026-09-04',
      totais: { ingredientes: 1, proximos_do_vencimento: 0, vencidos: 0 },
      ingredientes: [{
        id: 1, nome: 'Farinha', estoque_atual: '6.000', meta_atual: '20.000',
        unidade_exibicao: 'Kg', validade: { situacao: 'dentro_da_validade', descricao: 'Dentro da validade' },
      }],
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    render(<MemoryRouter><App /></MemoryRouter>)

    expect(screen.getByText('Carregando o estoque…')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('Farinha')).toBeInTheDocument())
    expect(screen.getByText('Ingredientes ativos').parentElement).toHaveTextContent('1')
  })

  it('mostra uma mensagem quando a API falha', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(
      JSON.stringify({ detail: 'Serviço indisponível.' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } },
    ))

    render(<MemoryRouter><App /></MemoryRouter>)

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Serviço indisponível.'))
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
  })

  it('apresenta página não encontrada para uma rota inválida', () => {
    render(<MemoryRouter initialEntries={['/rota-inexistente']}><App /></MemoryRouter>)

    expect(screen.getByRole('heading', { name: 'Página não encontrada' })).toBeInTheDocument()
    expect(screen.getByText('O endereço informado não existe ou não está mais disponível.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Voltar ao painel' })).toHaveAttribute('href', '/')
  })
})
