import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Office Agent · 工作现场",
  description: "基于 FORTE 公开办公场景的可观察 Agent 工作现场",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
