
### Настройка видеокарты на хосте
```bash
# Добавление репозитория NVIDIA
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Обновление и установка
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
```

### Настройка докера
```bash
# Настройка NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker

# Перезапустите Docker daemon
sudo systemctl restart docker
```

### Проверка 
```bash
# Проверка, что NVIDIA runtime доступен
docker info | grep -i runtime

# Должно показать что-то вроде:
# Runtimes: nvidia runc io.containerd.runc.v2
```