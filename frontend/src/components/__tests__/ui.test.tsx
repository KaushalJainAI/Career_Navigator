import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { RichText } from '../copilot/RichText';
import { FitRing, salaryLabel, timeAgo } from '../ui';

describe('RichText', () => {
  it('renders bold and bullets', () => {
    render(<RichText text={'**Zoho** comes first.\n• Revise SQL\n2. Practise DSA'} />);
    expect(screen.getByText('Zoho').tagName).toBe('STRONG');
    expect(screen.getByText('Revise SQL')).toBeInTheDocument();
    expect(screen.getByText('2.')).toBeInTheDocument();
  });

  it('never injects HTML from model output', () => {
    const { container } = render(<RichText text={'<img src=x onerror="alert(1)"> hi'} />);
    expect(container.querySelector('img')).toBeNull();
    expect(container.textContent).toContain('<img');
  });
});

describe('ui helpers', () => {
  it('formats salaries and relative time', () => {
    expect(salaryLabel(1200000, 1800000, 'INR')).toBe('INR 1200k–1800k');
    expect(salaryLabel(null, null, '')).toBe('');
    expect(timeAgo(new Date().toISOString())).toBe('today');
    expect(timeAgo(new Date(Date.now() - 3 * 86400000).toISOString())).toBe('3 days ago');
  });

  it('shows a dash when there is no fit yet', () => {
    render(<FitRing fit={null} verdict={null} />);
    expect(screen.getByText('—')).toBeInTheDocument();
    render(<FitRing fit={72} verdict="strong" />);
    expect(screen.getByText('72')).toBeInTheDocument();
  });
});
