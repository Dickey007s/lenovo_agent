export type QuoteLineItem = {
  name?: string;
  qty?: number;
  unit_price?: number;
  discount?: number;
  subtotal?: number;
};

export type QuoteSummary = {
  items: QuoteLineItem[];
  standardTotal: number | null;
  discountedTotal: number | null;
  savingsAmount: number | null;
  effectivePriceRatio: number | null;
  savingsRate: number | null;
  effectivePricePercent: string | null;
  effectivePriceZhe: string | null;
  savingsPercent: string | null;
  approvedFloorPercent: string | null;
  approvedFloorZhe: string | null;
  belowFloorItems: string[];
  errors: string[];
  valid: boolean;
};

type DecimalFraction = {
  numerator: bigint;
  denominator: bigint;
  decimalPlaces: number;
};

const MAX_INPUT = 10_000_000_000;
const MAX_ITEMS = 100;
const MAX_DECIMAL_PLACES = 8;
const MAX_SAFE_CENTS = 100_000_000_000_000n;


function decimalFraction(value: number): DecimalFraction {
  const [coefficient, exponentText = "0"] = String(value).toLowerCase().split("e");
  const exponent = Number(exponentText);
  const negative = coefficient.startsWith("-");
  const unsigned = negative ? coefficient.slice(1) : coefficient;
  const [integerPart, fractionalPart = ""] = unsigned.split(".");
  const digits = `${integerPart || "0"}${fractionalPart}`.replace(/^0+(?=\d)/, "") || "0";
  const decimalPlaces = fractionalPart.length - exponent;
  let numerator = BigInt(digits);
  let denominator = 1n;
  if (decimalPlaces > 0) denominator = 10n ** BigInt(decimalPlaces);
  if (decimalPlaces < 0) numerator *= 10n ** BigInt(-decimalPlaces);
  if (negative) numerator = -numerator;
  return { numerator, denominator, decimalPlaces: Math.max(decimalPlaces, 0) };
}


function validateNumber(
  value: unknown,
  label: string,
  errors: string[],
  options: { max?: number } = {},
): value is number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    errors.push(`${label}缺失或不是有效数字`);
    return false;
  }
  if (value < 0 || value > (options.max ?? MAX_INPUT)) {
    errors.push(`${label}超出可核算范围`);
    return false;
  }
  if (decimalFraction(value).decimalPlaces > MAX_DECIMAL_PLACES) {
    errors.push(`${label}最多支持 ${MAX_DECIMAL_PLACES} 位小数`);
    return false;
  }
  return true;
}


function roundHalfUp(numerator: bigint, denominator: bigint) {
  const quotient = numerator / denominator;
  const remainder = numerator % denominator;
  return remainder * 2n >= denominator ? quotient + 1n : quotient;
}


function standardLineCents(quantity: number, unitPrice: number) {
  const quantityFraction = decimalFraction(quantity);
  const priceFraction = decimalFraction(unitPrice);
  return roundHalfUp(
    quantityFraction.numerator * priceFraction.numerator * 100n,
    quantityFraction.denominator * priceFraction.denominator,
  );
}


function discountedLineCents(standardCents: bigint, discount: number) {
  const discountFraction = decimalFraction(discount);
  return roundHalfUp(
    standardCents * discountFraction.numerator,
    discountFraction.denominator,
  );
}


function centsToNumber(value: bigint) {
  if (value > MAX_SAFE_CENTS) throw new RangeError("金额超出浏览器可安全显示范围");
  return Number(value) / 100;
}


function formatHundredths(value: bigint) {
  return `${value / 100n}.${String(value % 100n).padStart(2, "0")}`;
}


function formatRatio(value: number, multiplier: bigint) {
  const fraction = decimalFraction(value);
  return formatHundredths(roundHalfUp(
    fraction.numerator * multiplier * 100n,
    fraction.denominator,
  ));
}


function formatFractionRatio(numerator: bigint, denominator: bigint, multiplier: bigint) {
  return formatHundredths(roundHalfUp(numerator * multiplier * 100n, denominator));
}


export function calculateQuoteSummary(
  items: QuoteLineItem[],
  approvedFloor?: number,
): QuoteSummary {
  const errors: string[] = [];
  if (!items.length) errors.push("当前报价没有可核算的行项目");
  if (items.length > MAX_ITEMS) errors.push(`报价行项目不能超过 ${MAX_ITEMS} 行`);

  let floorIsValid = false;
  if (approvedFloor !== undefined) {
    floorIsValid = validateNumber(approvedFloor, "最低折后比例", errors, { max: 1 });
  }
  const approvedFloorPercent = floorIsValid && approvedFloor !== undefined
    ? formatRatio(approvedFloor, 100n)
    : null;
  const approvedFloorZhe = floorIsValid && approvedFloor !== undefined
    ? formatRatio(approvedFloor, 10n)
    : null;

  let standardCents = 0n;
  let discountedCents = 0n;
  const belowFloorItems: string[] = [];
  const normalizedItems = items.map((item, index) => {
    const lineErrors: string[] = [];
    const quantity = item.qty;
    const unitPrice = item.unit_price;
    const discount = item.discount;
    const quantityValid = validateNumber(quantity, `第 ${index + 1} 行数量`, lineErrors);
    const priceValid = validateNumber(unitPrice, `第 ${index + 1} 行标准价`, lineErrors);
    const discountValid = validateNumber(
      discount,
      `第 ${index + 1} 行折后比例`,
      lineErrors,
      { max: 1 },
    );
    errors.push(...lineErrors);
    if (!quantityValid || !priceValid || !discountValid) {
      return { ...item, subtotal: undefined };
    }

    try {
      const listCents = standardLineCents(quantity as number, unitPrice as number);
      const netCents = discountedLineCents(listCents, discount as number);
      standardCents += listCents;
      discountedCents += netCents;
      if (standardCents > MAX_SAFE_CENTS || discountedCents > MAX_SAFE_CENTS) {
        throw new RangeError("金额超出浏览器可安全显示范围");
      }
      if (floorIsValid && approvedFloor !== undefined && (discount as number) < approvedFloor) {
        belowFloorItems.push(item.name || `第 ${index + 1} 行`);
      }
      return { ...item, subtotal: centsToNumber(netCents) };
    } catch (error) {
      errors.push(error instanceof Error ? error.message : `第 ${index + 1} 行无法核算`);
      return { ...item, subtotal: undefined };
    }
  });

  if (errors.length) {
    return {
      items: normalizedItems,
      standardTotal: null,
      discountedTotal: null,
      savingsAmount: null,
      effectivePriceRatio: null,
      savingsRate: null,
      effectivePricePercent: null,
      effectivePriceZhe: null,
      savingsPercent: null,
      approvedFloorPercent,
      approvedFloorZhe,
      belowFloorItems: [],
      errors,
      valid: false,
    };
  }

  const savingsCents = standardCents - discountedCents;
  const standardTotal = centsToNumber(standardCents);
  const discountedTotal = centsToNumber(discountedCents);
  const savingsAmount = centsToNumber(savingsCents);
  const effectivePriceRatio = standardCents > 0n
    ? Number(discountedCents) / Number(standardCents)
    : null;
  const effectivePricePercent = standardCents > 0n
    ? formatFractionRatio(discountedCents, standardCents, 100n)
    : null;
  const effectivePriceZhe = standardCents > 0n
    ? formatFractionRatio(discountedCents, standardCents, 10n)
    : null;
  const savingsPercent = standardCents > 0n
    ? formatFractionRatio(savingsCents, standardCents, 100n)
    : null;

  return {
    items: normalizedItems,
    standardTotal,
    discountedTotal,
    savingsAmount,
    effectivePriceRatio,
    savingsRate: effectivePriceRatio === null ? null : 1 - effectivePriceRatio,
    effectivePricePercent,
    effectivePriceZhe,
    savingsPercent,
    approvedFloorPercent,
    approvedFloorZhe,
    belowFloorItems,
    errors: [],
    valid: true,
  };
}


export function updateQuoteItem(
  items: QuoteLineItem[],
  index: number,
  patch: Partial<QuoteLineItem>,
  approvedFloor?: number,
) {
  return calculateQuoteSummary(
    items.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item),
    approvedFloor,
  );
}
