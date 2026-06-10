import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useApplicationsStore } from '../useApplicationsStore';
import { Applications } from '../../api/endpoints';

vi.mock('../../api/endpoints', () => ({
  Applications: {
    list: vi.fn(),
    create: vi.fn(),
    patch: vi.fn(),
  },
}));

describe('useApplicationsStore', () => {
  beforeEach(() => {
    useApplicationsStore.setState({ applications: [] });
    vi.clearAllMocks();
  });

  it('keeps nested job details from the applications API', async () => {
    vi.mocked(Applications.list).mockResolvedValue([
      {
        id: 1,
        job: 10,
        status: 'saved',
        tier_used: 'assist',
        job_detail: {
          id: 10,
          title: 'Backend Engineer',
          company: { name: 'Acme' },
          location: 'Remote',
        },
      },
    ]);

    await useApplicationsStore.getState().fetch();

    expect(useApplicationsStore.getState().applications[0].job_detail?.title).toBe('Backend Engineer');
    expect(useApplicationsStore.getState().applications[0].job_detail?.company?.name).toBe('Acme');
  });

  it('updates status locally after patch succeeds', async () => {
    useApplicationsStore.setState({
      applications: [{ id: 1, job: 10, status: 'saved', tier_used: 'assist' }],
    });
    vi.mocked(Applications.patch).mockResolvedValue({ id: 1, status: 'applied' });

    await useApplicationsStore.getState().setStatus(1, 'applied');

    expect(Applications.patch).toHaveBeenCalledWith(1, { status: 'applied' });
    expect(useApplicationsStore.getState().applications[0].status).toBe('applied');
  });
});
