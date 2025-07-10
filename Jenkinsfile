pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/tjfrhrtks12/back-testdev-0710.git'
            }
        }

        stage('Run Python') {
            steps {
                sh 'python3 main.py'
            }
        }
    }
}
