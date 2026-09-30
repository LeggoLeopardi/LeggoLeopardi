const app = require('./app');

const port = Number(process.env.PORT) || 8000;
app.listen(port, () => console.log(`LeggoLeopardi on http://localhost:${port}`));
