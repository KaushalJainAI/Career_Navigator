import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { JobDetail } from './JobDetail';
import { Applications, Jobs, Tailoring } from '../../api/endpoints';

vi.mock('../../api/endpoints', () => ({
  Jobs: {
    detail: vi.fn(),
    match: vi.fn(),
  },
  Applications: {
    prepare: vi.fn(),
  },
  Tailoring: {
    resume: vi.fn(),
    coverLetter: vi.fn(),
  },
}));

describe('JobDetail apply workflow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(Jobs.detail).mockResolvedValue({
      id: 7,
      title: 'Backend Engineer',
      description: '<p>Build APIs.</p>',
      apply_url: 'https://example.com/apply',
      company: { name: 'Acme' },
    });
    vi.mocked(Jobs.match).mockResolvedValue({
      score: 0.82,
      breakdown: {},
      gaps: [],
    });
    vi.mocked(Tailoring.resume).mockResolvedValue({
      id: 1,
      content: { raw_text: 'Tailored resume text' },
    });
    vi.mocked(Tailoring.coverLetter).mockResolvedValue({
      id: 2,
      content: 'Cover letter text',
    });
  });

  it('prepares autonomous review and shows approval state', async () => {
    vi.mocked(Applications.prepare).mockResolvedValue({
      tier: 'autonomous',
      status: 'ready',
      apply_url: 'https://example.com/apply',
      approval_token: 'approval-token',
      next_actions: ['Review the prepared application package.'],
      application: { id: 123 },
    });

    render(
      <MemoryRouter initialEntries={['/jobs/7']}>
        <Routes>
          <Route path="/jobs/:id" element={<JobDetail />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole('button', { name: 'Autonomous review' }));

    await waitFor(() => {
      expect(Applications.prepare).toHaveBeenCalledWith(7, 'autonomous');
    });
    expect(await screen.findByText('Autonomous flow is paused for review')).toBeInTheDocument();
    expect(screen.getByText('Approval token issued')).toBeInTheDocument();
  });

  it('generates and displays application materials after preparation', async () => {
    vi.mocked(Applications.prepare).mockResolvedValue({
      tier: 'assist',
      status: 'saved',
      apply_url: 'https://example.com/apply',
      approval_token: '',
      next_actions: ['Generate a tailored resume or cover letter.'],
      application: { id: 123 },
    });

    render(
      <MemoryRouter initialEntries={['/jobs/7']}>
        <Routes>
          <Route path="/jobs/:id" element={<JobDetail />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole('button', { name: 'Assist apply' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Generate materials' }));

    await waitFor(() => {
      expect(Tailoring.resume).toHaveBeenCalledWith(123);
      expect(Tailoring.coverLetter).toHaveBeenCalledWith(123);
    });
    expect(await screen.findByText('Tailored resume text')).toBeInTheDocument();
    expect(screen.getByText('Cover letter text')).toBeInTheDocument();
  });
});
