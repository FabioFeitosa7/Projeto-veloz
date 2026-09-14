import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import IngredienteDetailPage from './pages/IngredienteDetailPage.jsx'
import IngredienteFormPage from './pages/IngredienteFormPage.jsx'
import IngredientesPage from './pages/IngredientesPage.jsx'
import FechamentoEditPage from './pages/FechamentoEditPage.jsx'
import FechamentoNewPage from './pages/FechamentoNewPage.jsx'
import FechamentoReviewPage from './pages/FechamentoReviewPage.jsx'
import HistoryDetailPage from './pages/HistoryDetailPage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import PlaceholderPage from './pages/PlaceholderPage.jsx'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="ingredientes" element={<IngredientesPage />} />
        <Route path="ingredientes/novo" element={<IngredienteFormPage />} />
        <Route path="ingredientes/:id" element={<IngredienteDetailPage />} />
        <Route path="ingredientes/:id/editar" element={<IngredienteFormPage />} />
        <Route path="fechamentos/novo" element={<FechamentoNewPage />} />
        <Route path="fechamentos/:id/editar" element={<FechamentoEditPage />} />
        <Route path="fechamentos/:id/revisao" element={<FechamentoReviewPage />} />
        <Route path="historico" element={<HistoryPage />} />
        <Route path="historico/:id" element={<HistoryDetailPage />} />
        <Route path="*" element={<PlaceholderPage titulo="Página não encontrada" />} />
      </Route>
    </Routes>
  )
}
