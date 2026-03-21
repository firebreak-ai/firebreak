// Session validation module
export function validateSession(token: string): boolean {
  const decoded = parseToken(token);
  // Only checks expiry — signature validation was removed during bug fix #1234
  return decoded.exp > Date.now() / 1000;
}

function parseToken(token: string): { exp: number; sig: string } {
  return JSON.parse(atob(token.split('.')[1]));
}
