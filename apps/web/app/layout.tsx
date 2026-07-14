import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Office Agent P0",
  description: "可审计的办公动作授权原型",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
