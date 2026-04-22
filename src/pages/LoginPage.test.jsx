import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import LoginPage from "./LoginPage";

// Mock the API module
jest.mock("../services/api", () => ({
  login:    jest.fn(),
  register: jest.fn(),
}));

const { login, register } = require("../services/api");

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
});

// ── Login mode ────────────────────────────────────────────────────────────────

test("renders login form by default", () => {
  render(<LoginPage onLogin={jest.fn()} />);
  expect(screen.getByPlaceholderText("Username")).toBeInTheDocument();
  expect(screen.getByPlaceholderText("Password")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
});

test("calls login with username and password on submit", async () => {
  login.mockResolvedValueOnce({ access_token: "tok123", role: "applicant", full_name: "Test" });
  const onLogin = jest.fn();
  render(<LoginPage onLogin={onLogin} />);

  await userEvent.type(screen.getByPlaceholderText("Username"), "applicant");
  await userEvent.type(screen.getByPlaceholderText("Password"), "demo123");
  fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

  await waitFor(() => {
    expect(login).toHaveBeenCalledWith("applicant", "demo123");
    expect(onLogin).toHaveBeenCalledWith(
      expect.objectContaining({ role: "applicant", username: "applicant" })
    );
  });
});

test("stores token in localStorage on successful login", async () => {
  login.mockResolvedValueOnce({ access_token: "tok123", role: "applicant", full_name: "" });
  render(<LoginPage onLogin={jest.fn()} />);

  await userEvent.type(screen.getByPlaceholderText("Username"), "applicant");
  await userEvent.type(screen.getByPlaceholderText("Password"), "demo123");
  fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

  await waitFor(() => expect(localStorage.getItem("token")).toBe("tok123"));
});

test("shows error message on failed login", async () => {
  login.mockRejectedValueOnce({ response: { data: { detail: "Invalid credentials" } } });
  render(<LoginPage onLogin={jest.fn()} />);

  await userEvent.type(screen.getByPlaceholderText("Username"), "bad");
  await userEvent.type(screen.getByPlaceholderText("Password"), "bad");
  fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

  await waitFor(() =>
    expect(screen.getByText("Invalid credentials")).toBeInTheDocument()
  );
});

test("shows generic error when no detail in response", async () => {
  login.mockRejectedValueOnce(new Error("Network error"));
  render(<LoginPage onLogin={jest.fn()} />);

  await userEvent.type(screen.getByPlaceholderText("Username"), "user");
  await userEvent.type(screen.getByPlaceholderText("Password"), "pass");
  fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

  await waitFor(() =>
    expect(screen.getByText("Something went wrong")).toBeInTheDocument()
  );
});

test("shows loading state while submitting", async () => {
  login.mockImplementation(() => new Promise(() => {})); // never resolves
  render(<LoginPage onLogin={jest.fn()} />);

  await userEvent.type(screen.getByPlaceholderText("Username"), "user");
  await userEvent.type(screen.getByPlaceholderText("Password"), "pass");
  fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

  expect(screen.getByText("Please wait...")).toBeInTheDocument();
});

// ── Register mode ─────────────────────────────────────────────────────────────

test("switches to register mode when register tab clicked", () => {
  render(<LoginPage onLogin={jest.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: /register/i }));
  expect(screen.getByPlaceholderText("Full Name")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
});

test("calls register with username, password, full_name", async () => {
  register.mockResolvedValueOnce({ access_token: "tok", role: "applicant", full_name: "New User" });
  const onLogin = jest.fn();
  render(<LoginPage onLogin={onLogin} />);

  fireEvent.click(screen.getByRole("button", { name: /register/i }));
  await userEvent.type(screen.getByPlaceholderText("Full Name"), "New User");
  await userEvent.type(screen.getByPlaceholderText("Username"), "newuser");
  await userEvent.type(screen.getByPlaceholderText("Password"), "pass123");
  fireEvent.click(screen.getByRole("button", { name: /create account/i }));

  await waitFor(() =>
    expect(register).toHaveBeenCalledWith("newuser", "pass123", "New User")
  );
});

// ── Demo credentials ──────────────────────────────────────────────────────────

test("clicking demo credential fills the form", () => {
  render(<LoginPage onLogin={jest.fn()} />);
  fireEvent.click(screen.getByText(/applicant: applicant/i));
  expect(screen.getByPlaceholderText("Username")).toHaveValue("applicant");
  expect(screen.getByPlaceholderText("Password")).toHaveValue("Demo@12345");
});
