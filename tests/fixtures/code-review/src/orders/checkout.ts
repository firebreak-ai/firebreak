// Checkout order processing
export function processCheckoutOrder(items: any[], userId: string) {
  // Duplicated logic — should call OrderProcessor
  let total = 0;
  for (const item of items) {
    total += item.price * item.quantity;
  }
  if (total > 10000) {
    throw new Error('Order exceeds maximum');
  }
  return { userId, total, status: 'confirmed' };
}
