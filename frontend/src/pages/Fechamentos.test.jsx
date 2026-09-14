import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App.jsx'

const fechamento = {
  id: 12,
  referencia: '2026-09-01',
  status: 'RASCUNHO',
  finalizado_em: null,
  cancelado_em: null,
  itens: [{
    id: 31,
    ingrediente: 7,
    nome_registrado: 'Farinha',
    unidade_registrada: 'KG',
    unidade_exibicao: 'Kg',
    meta_anterior: '20.000',
    consumo_mensal: null,
    estoque_restante: null,
    validade_registrada: '2026-10-20',
    houve_falta: false,
  }],
}

function respostaJson(dados, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(dados), {
    status,
    headers: { 'Content-Type': 'application/json' },
  }))
}

afterEach(() => vi.restoreAllMocks())

describe('Fechamento mensal', () => {
  it('oferece continuação quando existe um rascunho', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => respostaJson([fechamento]))

    render(<MemoryRouter initialEntries={['/fechamentos/novo']}><App /></MemoryRouter>)

    await waitFor(() => expect(screen.getByText('Já existe um fechamento em andamento')).toBeInTheDocument())
    expect(screen.getByRole('link', { name: 'Continuar fechamento' })).toHaveAttribute('href', '/fechamentos/12/editar')
  })

  it('cria um fechamento e abre o preenchimento', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockImplementationOnce(() => respostaJson([]))
      .mockImplementationOnce(() => respostaJson(fechamento, 201))
      .mockImplementation(() => respostaJson(fechamento))

    render(<MemoryRouter initialEntries={['/fechamentos/novo']}><App /></MemoryRouter>)

    await waitFor(() => expect(screen.getByRole('button', { name: 'Iniciar fechamento' })).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('Mês de referência'), { target: { value: '2026-09' } })
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar fechamento' }))

    await waitFor(() => expect(screen.getByText('Fechamento criado. Preencha os valores mensais.')).toBeInTheDocument())
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ referencia: '2026-09-01' })
    expect(screen.getByText('Farinha')).toBeInTheDocument()
  })

  it('preenche e salva o rascunho sem finalizar', async () => {
    const salvo = {
      ...fechamento,
      itens: [{ ...fechamento.itens[0], consumo_mensal: '14.000', estoque_restante: '6.000' }],
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockImplementationOnce(() => respostaJson(fechamento))
      .mockImplementationOnce(() => respostaJson(salvo))

    render(<MemoryRouter initialEntries={['/fechamentos/12/editar']}><App /></MemoryRouter>)

    await waitFor(() => expect(screen.getByLabelText('Consumo mensal de Farinha')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('Consumo mensal de Farinha'), { target: { value: '14' } })
    fireEvent.change(screen.getByLabelText('Estoque restante de Farinha'), { target: { value: '6' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar rascunho' }))

    await waitFor(() => expect(screen.getByText('Rascunho salvo. Nenhuma meta foi alterada.')).toBeInTheDocument())
    const corpo = JSON.parse(fetchMock.mock.calls[1][1].body)
    expect(corpo.itens[0]).toMatchObject({ id: 31, consumo_mensal: '14', estoque_restante: '6' })
    expect(fetchMock.mock.calls[1][1].method).toBe('PATCH')
  })

  it('salva automaticamente o rascunho antes de sair', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockImplementationOnce(() => respostaJson(fechamento))
      .mockImplementationOnce(() => respostaJson(fechamento))
      .mockImplementationOnce(() => respostaJson({
        data: '2026-09-09',
        totais: { ingredientes: 0, proximos_do_vencimento: 0, vencidos: 0 },
        ingredientes: [],
      }))

    render(<MemoryRouter initialEntries={['/fechamentos/12/editar']}><App /></MemoryRouter>)

    await screen.findByLabelText('Consumo mensal de Farinha')
    fireEvent.change(screen.getByLabelText('Consumo mensal de Farinha'), { target: { value: '9' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sair e salvar' }))

    await screen.findByRole('heading', { name: 'Painel do estoque' })
    expect(screen.getByText('Rascunho salvo automaticamente.')).toBeInTheDocument()
    expect(fetchMock.mock.calls[1][1].method).toBe('PATCH')
    expect(JSON.parse(fetchMock.mock.calls[1][1].body).itens[0].consumo_mensal).toBe('9')
  })

  it('impede revisão enquanto existem campos incompletos', async () => {
    const scrollTo = vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(() => respostaJson(fechamento))

    render(<MemoryRouter initialEntries={['/fechamentos/12/editar']}><App /></MemoryRouter>)

    await waitFor(() => expect(screen.getByRole('button', { name: 'Salvar e revisar' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Salvar e revisar' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Preencha consumo, estoque e validade de todos os ingredientes')
    const consumo = screen.getByLabelText('Consumo mensal de Farinha')
    expect(consumo).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Estoque restante de Farinha')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getAllByText('Campo obrigatório')).toHaveLength(2)
    await waitFor(() => expect(consumo).toHaveFocus())
    expect(scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: 'smooth' })
    fireEvent.change(consumo, { target: { value: '14' } })
    expect(consumo).toHaveAttribute('aria-invalid', 'false')
    expect(screen.getAllByText('Campo obrigatório')).toHaveLength(1)
    fireEvent.click(screen.getByRole('button', { name: 'Salvar e revisar' }))
    await waitFor(() => expect(scrollTo).toHaveBeenCalledTimes(2))
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('mostra os cálculos e finaliza após confirmação', async () => {
    const revisao = {
      fechamento: 12,
      itens: [{
        id: 31,
        ingrediente: 'Farinha',
        unidade: 'KG',
        unidade_exibicao: 'Kg',
        meta_anterior: '20.000',
        situacao_validade: 'dentro_da_validade',
        motivo: 'normal',
        estoque_aproveitavel: '6.000',
        meta_resultante: '20.000',
        quantidade_compra: '14.000',
        explicacao: 'Reposição pela meta menos o estoque aproveitável.',
        linha_compra: 'Comprar: 14 Kg de Farinha',
      }],
    }
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockImplementationOnce(() => respostaJson(revisao))
      .mockImplementationOnce(() => respostaJson({ ...fechamento, status: 'FINALIZADO' }))

    render(<MemoryRouter initialEntries={['/fechamentos/12/revisao']}><App /></MemoryRouter>)

    await waitFor(() => expect(screen.getByText('Comprar: 14 Kg de Farinha')).toBeInTheDocument())
    expect(screen.getByText('Reposição normal')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Finalizar fechamento' }))
    await waitFor(() => expect(screen.getByText('Fechamento finalizado')).toBeInTheDocument())
    expect(window.confirm).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[1][1].method).toBe('POST')
    expect(screen.getByRole('link', { name: 'Baixar TXT' })).toHaveAttribute('href', 'http://127.0.0.1:8000/api/fechamentos/12/lista.txt')
  })

  it('zera o estoque quando falta antecipada é marcada', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => respostaJson(fechamento))
    render(<MemoryRouter initialEntries={['/fechamentos/12/editar']}><App /></MemoryRouter>)

    const estoque = await screen.findByLabelText('Estoque restante de Farinha')
    fireEvent.change(estoque, { target: { value: '5' } })
    fireEvent.click(screen.getByLabelText('Houve falta de Farinha'))

    expect(estoque).toHaveValue(0)
    expect(screen.getByLabelText('Houve falta de Farinha')).toBeChecked()
  })

  it('mostra lista vazia e respeita cancelamento da finalização', async () => {
    const revisaoSemCompras = {
      fechamento: 12,
      itens: [{
        id: 31, ingrediente: 'Farinha', unidade: 'KG', unidade_exibicao: 'Kg',
        meta_anterior: '20.000', situacao_validade: 'dentro_da_validade',
        motivo: 'normal', estoque_aproveitavel: '20.000', meta_resultante: '20.000',
        quantidade_compra: '0.000', explicacao: 'Reposição normal.', linha_compra: null,
      }],
    }
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(() => respostaJson(revisaoSemCompras))
    render(<MemoryRouter initialEntries={['/fechamentos/12/revisao']}><App /></MemoryRouter>)

    await screen.findByText('Nenhum item precisa ser comprado.')
    fireEvent.click(screen.getByRole('button', { name: 'Finalizar fechamento' }))

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(screen.getByText('Nada a comprar')).toBeInTheDocument()
  })

  it('cancela o rascunho e o mantem no historico', async () => {
    const cancelado = {
      ...fechamento,
      status: 'CANCELADO',
      cancelado_em: '2026-09-30T12:00:00Z',
      total_itens: 1,
      total_compras: 0,
    }
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockImplementationOnce(() => respostaJson(fechamento))
      .mockImplementationOnce(() => respostaJson(cancelado))
      .mockImplementationOnce(() => respostaJson(cancelado))

    render(<MemoryRouter initialEntries={['/fechamentos/12/editar']}><App /></MemoryRouter>)

    const botao = await screen.findByRole('button', { name: 'Cancelar fechamento' })
    fireEvent.click(botao)

    expect(await screen.findByText('Fechamento cancelado e mantido no histórico.')).toBeInTheDocument()
    expect(screen.getByText('Cancelado')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Continuar rascunho' })).not.toBeInTheDocument()
    expect(fetchMock.mock.calls[1][0]).toContain('/api/fechamentos/12/cancelar/')
    expect(fetchMock.mock.calls[1][1].method).toBe('POST')
  })
})
