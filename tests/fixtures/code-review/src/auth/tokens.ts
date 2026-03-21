// Token utilities
export function createToken(userId: string, expiresIn: number): string {
  const payload = { sub: userId, exp: Math.floor(Date.now() / 1000) + expiresIn };
  return btoa(JSON.stringify({ alg: 'HS256' })) + '.' + btoa(JSON.stringify(payload)) + '.signature';
}
