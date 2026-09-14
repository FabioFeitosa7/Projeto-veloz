const rotulos = {
  dentro_da_validade: 'Dentro da validade',
  proximo_do_vencimento: 'Próximo do vencimento',
  vence_hoje: 'Vence hoje',
  vencido: 'Vencido',
}

export default function IngredientStatus({ validade }) {
  return (
    <span className={`badge badge-${validade.situacao}`}>
      {rotulos[validade.situacao] || validade.descricao}
    </span>
  )
}
