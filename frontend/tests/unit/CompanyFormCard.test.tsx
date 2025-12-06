import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CompanyFormCard } from '@/components/(forms)';
import { BrowserRouter } from 'react-router-dom';

// Since we can't easily mock the API and toast in this environment,
// we'll focus on testing the rendering and basic interactions

describe('CompanyFormCard', () => {
  it('renders the form correctly', () => {
    render(
      <BrowserRouter>
        <CompanyFormCard />
      </BrowserRouter>
    );

    expect(screen.getByText('Новая компания')).toBeInTheDocument();
    expect(screen.getByLabelText('Название компании *')).toBeInTheDocument();
    expect(screen.getByLabelText('URL slug *')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Телефон')).toBeInTheDocument();
    expect(screen.getByText('Хранилище файлов')).toBeInTheDocument();
    expect(screen.getByLabelText('Квота хранилища (ГБ)')).toBeInTheDocument();
  });

  it('autogenerates slug from company name', async () => {
    render(
      <BrowserRouter>
        <CompanyFormCard />
      </BrowserRouter>
    );

    const nameInput = screen.getByLabelText('Название компании *');
    fireEvent.change(nameInput, { target: { value: 'Test Company Name' } });

    // Wait for the slug to be updated
    await waitFor(() => {
      const slugInput = screen.getByLabelText('URL slug *');
      expect(slugInput).toHaveValue('test-company-name');
    });
  });
});