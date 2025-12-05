import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Login } from '@/pages/Login';
import userEvent from '@testing-library/user-event';
import { waitFor } from '@testing-library/react';

// Helper to render with router
const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('Login Page', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should render login form with email and password fields', () => {
    renderWithRouter(<Login />);
    
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/пароль/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /войти/i })).toBeInTheDocument();
  });

  it('should show validation errors for empty fields', async () => {
    const user = userEvent.setup();
    renderWithRouter(<Login />);
    
    const submitButton = screen.getByRole('button', { name: /войти/i });
    await user.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/email обязателен/i)).toBeInTheDocument();
    });
  });

  it('should show validation error for invalid email format', async () => {
    const user = userEvent.setup();
    renderWithRouter(<Login />);
    
    const emailInput = screen.getByLabelText(/email/i);
    await user.type(emailInput, 'invalid-email');
    
    const submitButton = screen.getByRole('button', { name: /войти/i });
    await user.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/неверный формат email/i)).toBeInTheDocument();
    });
  });

  it('should successfully login with valid credentials', async () => {
    const user = userEvent.setup();
    renderWithRouter(<Login />);
    
    await user.type(screen.getByLabelText(/email/i), 'admin@test.com');
    await user.type(screen.getByLabelText(/пароль/i), 'password123');
    await user.click(screen.getByRole('button', { name: /войти/i }));
    
    await waitFor(() => {
      // Should redirect after successful login
      expect(window.location.pathname).toBe('/dashboard');
    });
  });

  it('should display error message on failed login', async () => {
    const user = userEvent.setup();
    renderWithRouter(<Login />);
    
    await user.type(screen.getByLabelText(/email/i), 'wrong@test.com');
    await user.type(screen.getByLabelText(/пароль/i), 'wrongpassword');
    await user.click(screen.getByRole('button', { name: /войти/i }));
    
    await waitFor(() => {
      expect(screen.getByText(/неверный email или пароль/i)).toBeInTheDocument();
    });
  });

  it('should toggle password visibility', async () => {
    const user = userEvent.setup();
    renderWithRouter(<Login />);
    
    const passwordInput = screen.getByLabelText(/пароль/i);
    expect(passwordInput).toHaveAttribute('type', 'password');
    
    const toggleButton = screen.getByRole('button', { name: /показать пароль/i });
    await user.click(toggleButton);
    
    expect(passwordInput).toHaveAttribute('type', 'text');
  });

  it('should disable submit button while loading', async () => {
    const user = userEvent.setup();
    renderWithRouter(<Login />);
    
    await user.type(screen.getByLabelText(/email/i), 'admin@test.com');
    await user.type(screen.getByLabelText(/пароль/i), 'password123');
    
    const submitButton = screen.getByRole('button', { name: /войти/i });
    await user.click(submitButton);
    
    expect(submitButton).toBeDisabled();
  });
});
