import { useState } from "react";
import { Button, Card, CardContent, Stack, TextField, Typography } from "@mui/material";
import api from "../../services/api";

const Login = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const submit = async () => {
    const { data } = await api.post("/api/auth/login", { username, password });
    if (data?.access_token) {
      localStorage.setItem("zella_token", data.access_token);
    }
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Login
        </Typography>
        <Stack spacing={2}>
          <TextField label="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button variant="contained" onClick={submit}>
            Sign In
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default Login;
