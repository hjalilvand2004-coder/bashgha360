import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import ThemeToggle, { applyTheme, getStoredTheme } from "../components/ThemeToggle";
import SmartAssistant, { MSU_ORIGIN } from "../components/SmartAssistant";

/** v1.6 — تم Aurora (شب پیش‌فرض/روز) + ویجت دستیار هوشمند «دانشگاه هوشمند من» */

describe("تم شب/روز (Aurora Premium)", () => {
  beforeEach(() => {
    cleanup();
    localStorage.clear();
    applyTheme("dark");
  });

  it("پیش‌فرض شب است و کلید آن را به روز می‌برد و ذخیره می‌کند", () => {
    expect(getStoredTheme()).toBe("dark");
    render(<ThemeToggle />);
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    const btn = screen.getByRole("button", { name: "تغییر به حالت روز" });
    fireEvent.click(btn); // در act اجرا می‌شود تا effect اعمال تم هم flush شود
    expect(document.documentElement.classList.contains("light")).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(localStorage.getItem("theme")).toBe("light");
  });

  it("تم ذخیره‌شدهٔ روز در mount بعدی حفظ می‌شود", () => {
    applyTheme("light");
    render(<ThemeToggle />);
    expect(document.documentElement.classList.contains("light")).toBe(true);
    expect(screen.getByRole("button", { name: "تغییر به حالت شب" })).toBeInTheDocument();
  });

  it("applyTheme هر دو کلاس را متقارن می‌کند", () => {
    applyTheme("light");
    expect(document.documentElement.classList.contains("light")).toBe(true);
    applyTheme("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });
});

describe("ویجت دستیار هوشمند «دانشگاه هوشمند من»", () => {
  beforeEach(() => {
    cleanup();
    document.getElementById("msu-agent-widget")?.remove();
    delete window.__MSU_AGENT_TOKEN;
  });
  afterEach(() => {
    document.getElementById("msu-agent-widget")?.remove();
    delete window.__MSU_AGENT_TOKEN;
  });

  it("اسکریپت رسمی ویجت را با موقعیت پایین‌چپ تزریق می‌کند", () => {
    render(<SmartAssistant />);
    const s = document.getElementById("msu-agent-widget") as HTMLScriptElement | null;
    expect(s).not.toBeNull();
    expect(s?.getAttribute("data-position")).toBe("bl");
    expect(s?.getAttribute("data-origin")).toBe(MSU_ORIGIN);
    expect(s?.getAttribute("data-agent-url")).toBeTruthy();
    expect(s?.src).toContain("/msu-agent-widget.js");
  });

  it("دوبار mount، اسکریپت تکراری نمی‌سازد", () => {
    render(<SmartAssistant />);
    render(<SmartAssistant />);
    expect(document.querySelectorAll("#msu-agent-widget").length).toBe(1);
  });
});
