import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from '../useAuthStore';

describe('useAuthStore', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, loading: false, error: null });
    localStorage.clear();
  });

  it('logout clears user and tokens', () => {
    localStorage.setItem('cn_access', 'a');
    localStorage.setItem('cn_refresh', 'r');
    useAuthStore.setState({ user: { id: 1, email: 'a@b' } });
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().user).toBeNull();
    expect(localStorage.getItem('cn_access')).toBeNull();
    expect(localStorage.getItem('cn_refresh')).toBeNull();
  });
});
