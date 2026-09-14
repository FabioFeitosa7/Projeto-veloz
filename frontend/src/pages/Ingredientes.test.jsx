import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App.jsx'

const ingrediente = {
  id: 7,
  nome: 'Farinha',
  unidade: 'KG',
  unidade_exibicao: 'Kg',
  meta_atual: '20.000',
  estoque_atual: '6.000',
  data_validade: '2026-10-20',
  ativo: true,
  validade: { situacao: 'dentro_da_validade', descricao: 'Dentro da validade' },
}

function respostaJson(dados, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(dados), {
    status,
    headers: { 'Content-Type': 'application/json' },
  }))
}

afterEach(() => vi.restoreAllMocks())

describe('Telas de ingredientes', () => {
  it('lista ingredientes e oferece acesso aos detalhes', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => respostaJson([ingrediente]))

    render(<MemoryRouter initialEntries={['/ingredientes']}><App /></MemoryRouter>)

    await waitFor(() => expect(screen.getByText('Farinha')).toBeInTheDocument())
    expect(screen.getByRole('link', { name: 'Novo ingrediente' })).toHaveAttribute('href', '/ingredientes/novo')
    expect(screen.getAllByText('Dentro da validade')).toHaveLength(2)
  })

  it('cadastra ingrediente e abre seu detalhe', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockImplementationOnce(() => respostaJson(ingrediente, 201))
      .mockImplementation(() => respostaJson(ingrediente))

    render(<MemoryRouter initialEntries={['/ingredientes/novo']}><App /></MemoryRouter>)

    fireEvent.change(screen.getByLabelText('Nome do ingrediente'), { target: { value: 'Farinha' } })
    fireEvent.change(screen.getByLabelText('Meta mensal'), { target: { value: '20' } })
    fireEvent.change(screen.getByLabelText('Estoque atual'), { target: { value: '6' } })
    fireEvent.change(screen.getByLabelText('Data de validade'), { target: { value: '2026-10-20' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar ingrediente' }))

    await waitFor(() => expect(screen.getByText('Ingrediente cadastrado com sucesso.')).toBeInTheDocument())
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).nome).toBe('Farinha')
  })

  it('desativa e permite reativar um ingrediente', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.spyOn(globalThis, 'fetch')
      .mockImplementationOnce(() => respostaJson(ingrediente))
      .mockImplementationOnce(() => respostaJson({ ...ingrediente, ativo: false }))

    render(<MemoryRouter initialEntries={['/ingredientes/7']}><App /></MemoryRouter>)

    await waitFor(() => expect(screen.getByRole('button', { name: 'Desativar' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Desativar' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Reativar' })).toBeInTheDocument())
    expect(window.confirm).toHaveBeenCalledWith('Desativar o ingrediente Farinha?')
  })

  it('envia busca e filtro para a API', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(() => respostaJson([]))
    render(<MemoryRouter initialEntries={['/ingredientes']}><App /></MemoryRouter>)

    await waitFor(() => expect(screen.getByText('Nenhum ingrediente encontrado para estes filtros.')).toBeInTheDocument())
    fireEvent.change(screen.getByPlaceholderText('Nome do ingrediente'), { target: { value: 'leite' } })
    fireEvent.change(screen.getByLabelText('Situação'), { target: { value: 'inativos' } })

    await waitFor(() => expect(fetchMock.mock.calls.at(-1)[0]).toContain('q=leite'))
    expect(fetchMock.mock.calls.at(-1)[0]).toContain('situacao=inativos')
  })

  it('apresenta erros de validação devolvidos pelo Django', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => respostaJson({
      nome: ['Já existe um ingrediente com este nome.'],
      meta_atual: ['A meta deve ser maior que zero.'],
    }, 400))

    render(<MemoryRouter initialEntries={['/ingredientes/novo']}><App /></MemoryRouter>)
    fireEvent.change(screen.getByLabelText('Nome do ingrediente'), { target: { value: 'Farinha' } })
    fireEvent.change(screen.getByLabelText('Meta mensal'), { target: { value: '0' } })
    fireEvent.change(screen.getByLabelText('Estoque atual'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Data de validade'), { target: { value: '2026-10-20' } })
    fireEvent.submit(screen.getByRole('button', { name: 'Salvar ingrediente' }).closest('form'))

    expect(await screen.findByText('Já existe um ingrediente com este nome.')).toBeInTheDocument()
    expect(screen.getByText('A meta deve ser maior que zero.')).toBeInTheDocument()
  })

  it('possui campos identificados e navegação principal acessível', () => {
    render(<MemoryRouter initialEntries={['/ingredientes/novo']}><App /></MemoryRouter>)

    expect(screen.getByRole('navigation', { name: 'Navegação principal' })).toBeInTheDocument()
    expect(screen.getByLabelText('Nome do ingrediente')).toBeRequired()
    expect(screen.getByLabelText('Meta mensal')).toBeRequired()
    expect(screen.getByLabelText('Data de validade')).toBeRequired()
  })
})
