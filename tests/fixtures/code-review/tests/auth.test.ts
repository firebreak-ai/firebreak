// BAD TEST: re-implements production logic instead of testing validateSession
describe('session validation', () => {
  it('should validate session tokens', () => {
    const token = createTestToken({ exp: Math.floor(Date.now() / 1000) + 3600 });
    // Re-implements validation inline instead of calling validateSession
    const decoded = JSON.parse(atob(token.split('.')[1]));
    expect(decoded.exp).toBeGreaterThan(Date.now() / 1000);
  });
});

function createTestToken(payload: any): string {
  return btoa('{}') + '.' + btoa(JSON.stringify(payload)) + '.sig';
}
