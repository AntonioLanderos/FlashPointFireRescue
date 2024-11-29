using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Collections.Generic;

// Definición de la clase FireRescueModelData
[System.Serializable]
public class FireRescueModelData
{
    public int current_step;
    public Dictionary<string, string> door_data;
    public int poi;
    public int simulation_status;
    public int survivor_losses;
    public int damage_tracker;
    public int[][] grid;
    public int[][] grid_walls;
    public List<string> fire;
}

// Definición de la clase FireRescueData que contiene FireRescueModelData
[System.Serializable]
public class FireRescueData
{
    public FireRescueModelData model;
}

public class WebClient : MonoBehaviour
{
    public string url = "http://localhost:8585";
    public GameObject doorPrefab;
    public GameObject wallPrefab;
    public GameObject poiPrefab;
    public GameObject firePrefab;
    public float cellSize = 1.0f;

    // Corrigiendo la definición del método GetDataFromServer
    IEnumerator GetDataFromServer()
    {
        UnityWebRequest request = UnityWebRequest.Get(url); // Cambié a GET si no necesitas enviar datos con la solicitud
        yield return request.SendWebRequest();

        if (request.result == UnityWebRequest.Result.Success)
        {
            Debug.Log("Response: " + request.downloadHandler.text);
            // Analiza el JSON recibido
            FireRescueData data = JsonUtility.FromJson<FireRescueData>(request.downloadHandler.text);

            SetupGrid(data.model.grid, data.model.grid_walls);
            SetupDoors(data.model.door_data);
            SetupFire(data.model.fire);

            Debug.Log("Current step: " + data.model.current_step);
            Debug.Log("Simulation Status: " + data.model.simulation_status);
            Debug.Log("Total damage: " + data.model.damage_tracker);
        }
        else
        {
            Debug.LogError("Error: " + request.error);
        }
    }

    void SetupGrid(int[][] grid, int[][] walls)
    {
        // Limpiar cualquier objeto anterior
        foreach (Transform child in transform)
        {
            Destroy(child.gameObject);
        }

        // Crear el grid de celdas
        for (int y = 0; y < grid.Length; y++)
        {
            for (int x = 0; x < grid[y].Length; x++)
            {
                // Crear un cubo para cada celda
                Vector3 position = new Vector3(x * cellSize, 0, y * cellSize);
                if (grid[y][x] == 1)
                {
                    // Crear celda
                }
                else if (grid[y][x] == 2)
                {
                    // Crear fuego o algo similar
                }

                // Crear paredes si las hay
                if (walls[y][x] == 1)
                {
                    Instantiate(wallPrefab, position, Quaternion.identity);
                }
            }
        }
    }

        void SetupDoors(Dictionary<string, string> doorData)
    {
        foreach (KeyValuePair<string, string> entry in doorData)
        {
            string[] positions = entry.Key.Split(',');
            Vector3 position = new Vector3(int.Parse(positions[0]), 0, int.Parse(positions[1]));
            // Crear puerta en la posición
            Instantiate(doorPrefab, position, Quaternion.identity);
        }
    }

        void SetupFire(List<string> firePositions)
    {
        foreach (string position in firePositions)
        {
            string[] coords = position.Split(' ');
            int x = int.Parse(coords[0]);
            int y = int.Parse(coords[1]);
            
            Vector3 firePosition = new Vector3(x * cellSize, 0, y * cellSize);
            Instantiate(firePrefab, firePosition, Quaternion.identity);  // Crear el fuego en la posición
        }
    }

    // Moved FetchData method out of the GetDataFromServer IEnumerator method
    public void FetchData()
    {
        StartCoroutine(GetDataFromServer());
    }
}


