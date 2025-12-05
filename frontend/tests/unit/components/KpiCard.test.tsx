import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { KpiCard } from '@/components/(analytics)/KpiCard';

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('KpiCard Component', () => {
  it('should render title and value', () => {
    renderWithRouter(
      <KpiCard
        title="Total Companies"
        value={45}
        icon={<span>📊</span>}
      />
    );

    expect(screen.getByText('Total Companies')).toBeInTheDocument();
    expect(screen.getByText('45')).toBeInTheDocument();
  });

  it('should render change percentage with positive trend', () => {
    renderWithRouter(
      <KpiCard
        title="Active Projects"
        value={120}
        change={15.5}
        icon={<span>📈</span>}
      />
    );

    expect(screen.getByText('+15.5%')).toBeInTheDocument();
    expect(screen.getByText('+15.5%')).toHaveClass('text-green-600');
  });

  it('should render change percentage with negative trend', () => {
    renderWithRouter(
      <KpiCard
        title="Storage Used"
        value={85}
        change={-5.2}
        icon={<span>💾</span>}
      />
    );

    expect(screen.getByText('-5.2%')).toBeInTheDocument();
    expect(screen.getByText('-5.2%')).toHaveClass('text-red-600');
  });

  it('should format large numbers', () => {
    renderWithRouter(
      <KpiCard
        title="Total Views"
        value={1567890}
        icon={<span>👁️</span>}
      />
    );

    expect(screen.getByText(/1\.5M|1,567,890/)).toBeInTheDocument();
  });

  it('should render with custom color', () => {
    renderWithRouter(
      <KpiCard
        title="Custom KPI"
        value={100}
        color="primary"
        icon={<span>🎯</span>}
      />
    );

    const card = screen.getByText('Custom KPI').closest('div');
    expect(card).toHaveClass('border-primary');
  });

  it('should render loading state', () => {
    renderWithRouter(
      <KpiCard
        title="Loading KPI"
        value={0}
        loading={true}
        icon={<span>⏳</span>}
      />
    );

    expect(screen.getByTestId('kpi-skeleton')).toBeInTheDocument();
  });
});
