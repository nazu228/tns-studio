export type ResultRow = {
  num: number;
  name: string;
  day: number;
  night: number;
  odn: number;
  total: number;
  control: number;
  diff: number;
  meters: string;
};

export type Totals = {
  day: number;
  night: number;
  odn: number;
  total: number;
};

export const domRows: ResultRow[] = [
  { num: 1, name: "ул. Ленина, д. 1", day: 140.5, night: 12.25, odn: 0, total: 152.75, control: 152.75, diff: 0, meters: "3 раб. / 1 рез." },
  { num: 2, name: "ул. Мира, д. 3", day: 75, night: 0, odn: 25, total: 100, control: 100, diff: 0, meters: "2 раб. / 0 рез." },
];

export const gorodRows: ResultRow[] = [
  { num: 1, name: "ул. Советская, д. 10", day: 180.75, night: 0, odn: 15.5, total: 196.25, control: 196.25, diff: 0, meters: "3 раб. / 0 рез." },
  { num: 2, name: "ул. Гагарина, д. 22", day: 120.5, night: 22.25, odn: 13.75, total: 156.5, control: 156.5, diff: 0, meters: "3 раб. / 0 рез." },
  { num: 3, name: "ул. Победы, д. 5", day: 111.25, night: 0, odn: 24.5, total: 135.75, control: 135.75, diff: 0, meters: "2 раб. / 0 рез." },
];

export const totals: Record<"dom" | "gorod", Totals> = {
  dom: { day: 215.5, night: 12.25, odn: 25, total: 252.75 },
  gorod: { day: 412.5, night: 22.25, odn: 53.75, total: 488.5 },
};

export const MONTHS = [
  "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
];

export const YEARS = ["2025", "2026", "2027", "2028", "2029", "2030"];
