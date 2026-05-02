# Setting up API endpoint

```
// api.tsx
import axios from 'axios'

const api = axios.create({
    baseURL: 'http://localhost:5000/api',
    withCredentials: true  // required to send Flask session cookie
})

export default api
```
